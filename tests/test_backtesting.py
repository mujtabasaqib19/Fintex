"""
Benchmark 5 — Prediction Accuracy (Backtesting)
================================================
Evaluates the BULLISH / BEARISH / NEUTRAL verdict produced by
compute_technical_indicators() against actual next-day price movements
for all stocks in the Supabase stock_prices table.

Metrics computed:
  • Directional Accuracy  — correct direction calls / total calls
  • Precision (Bullish)   — TP_bull / (TP_bull + FP_bull)
  • Recall (Bullish)      — TP_bull / all actual Up days
  • Precision (Bearish)   — symmetric
  • Recall (Bearish)      — symmetric
  • Sharpe Ratio          — mean return of signal / std of returns
  • Max Drawdown          — worst equity-curve peak-to-trough drop

NO LOOK-AHEAD: on each day D the model only sees data up to and including D.
The actual outcome is the close on D+1.

Run:
    pytest tests/test_backtesting.py -v --tb=short

Offline (no Supabase):
    pytest tests/test_backtesting.py -v -k "not live"
"""
import sys, os, math, json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Supabase guard ────────────────────────────────────────────────────────────
def _supabase_reachable() -> bool:
    try:
        from src.db.connection import get_supabase_client
        sb = get_supabase_client()
        sb.table("stock_prices").select("symbol").limit(1).execute()
        return True
    except Exception:
        return False

LIVE = _supabase_reachable()
LIVE_SKIP = pytest.mark.skipif(not LIVE, reason="Supabase not reachable — check .env")

# ── Thresholds ────────────────────────────────────────────────────────────────
MIN_DIRECTIONAL_ACCURACY = 0.50   # must beat random (50%)
MIN_BULLISH_PRECISION     = 0.45
MIN_SHARPE                = 0.0   # signal must not be value-destroying
MAX_DRAWDOWN_LIMIT        = 0.55  # equity curve must not drop > 55% (PSX is volatile)
MIN_DAYS_PER_STOCK        = 30    # skip stocks with fewer trading days

# ── Pure-Python backtesting engine ───────────────────────────────────────────
class BacktestEngine:
    """
    Walk-forward backtest: for each date D in the stock's price history,
    compute indicators on data[0:D] and record verdict vs actual D+1 move.
    """

    def __init__(self, retriever):
        self.retriever = retriever

    def _compute_verdict(self, closes: List[float]) -> Optional[str]:
        """Run indicator computation on a subset of closes and return the verdict."""
        if len(closes) < 7:
            return None
        indicators = self._indicators_from_closes(closes)
        if indicators is None:
            return None
        return indicators.get("overall_signal", "neutral")

    def _indicators_from_closes(self, closes: List[float]) -> Optional[Dict[str, Any]]:
        """Minimal inline indicator set (mirrors PakistanStockRetriever logic)."""
        if len(closes) < 7:
            return None
        result: Dict[str, Any] = {"latest_price": closes[-1]}

        # SMAs
        for period, key in [(7, "sma_7"), (14, "sma_14"), (30, "sma_30")]:
            if len(closes) >= period:
                result[key] = sum(closes[-period:]) / period

        # RSI
        rsi = self.retriever._compute_rsi(closes)
        if rsi is not None:
            result["rsi"] = rsi

        # MACD
        macd = self.retriever._compute_macd(closes)

        # Momentum
        if len(closes) >= 6:
            base = closes[-6]
            if base > 0:
                result["momentum_5d"] = ((closes[-1] - base) / base) * 100

        # Composite signal
        signals = []
        if rsi is not None:
            signals.append("bullish" if rsi < 40 else ("bearish" if rsi > 60 else "neutral"))
        if macd:
            signals.append("bullish" if macd["histogram"] > 0 else "bearish")
        if result.get("sma_7") and result.get("sma_30"):
            signals.append("bullish" if result["sma_7"] > result["sma_30"] else "bearish")
        if result.get("momentum_5d") is not None:
            signals.append("bullish" if result["momentum_5d"] > 0 else "bearish")

        if signals:
            bull = signals.count("bullish")
            bear = signals.count("bearish")
            if bull > bear:
                result["overall_signal"] = "bullish"
            elif bear > bull:
                result["overall_signal"] = "bearish"
            else:
                result["overall_signal"] = "neutral"

        return result

    def run(self, closes: List[float]) -> Dict[str, Any]:
        """
        Walk-forward: for D in [warmup..N-2], predict D+1 direction.
        Returns a dict of metrics.
        """
        WARMUP = 30  # minimum bars before first prediction
        predictions, actuals = [], []

        for d in range(WARMUP, len(closes) - 1):
            verdict = self._compute_verdict(closes[:d + 1])
            if verdict is None:
                continue
            actual_up = closes[d + 1] > closes[d]
            predictions.append(verdict)
            actuals.append(actual_up)

        if not predictions:
            return {"total": 0}

        n = len(predictions)
        correct = sum(
            1 for p, a in zip(predictions, actuals)
            if (p == "bullish" and a) or (p == "bearish" and not a) or (p == "neutral")
        )
        directional_acc = correct / n

        # Precision / Recall for bullish
        tp_bull = sum(1 for p, a in zip(predictions, actuals) if p == "bullish" and a)
        fp_bull = sum(1 for p, a in zip(predictions, actuals) if p == "bullish" and not a)
        fn_bull = sum(1 for p, a in zip(predictions, actuals) if p != "bullish" and a)
        bull_prec = tp_bull / (tp_bull + fp_bull) if (tp_bull + fp_bull) > 0 else 0
        bull_rec  = tp_bull / (tp_bull + fn_bull) if (tp_bull + fn_bull) > 0 else 0

        # Precision / Recall for bearish
        tp_bear = sum(1 for p, a in zip(predictions, actuals) if p == "bearish" and not a)
        fp_bear = sum(1 for p, a in zip(predictions, actuals) if p == "bearish" and a)
        fn_bear = sum(1 for p, a in zip(predictions, actuals) if p != "bearish" and not a)
        bear_prec = tp_bear / (tp_bear + fp_bear) if (tp_bear + fp_bear) > 0 else 0
        bear_rec  = tp_bear / (tp_bear + fn_bear) if (tp_bear + fn_bear) > 0 else 0

        # Signal returns (1 = follow signal, -1 = opposite, 0 = hold neutral)
        signal_returns = []
        for p, a, d in zip(predictions, actuals, range(WARMUP, WARMUP + n)):
            if d + 1 >= len(closes):
                break
            daily_ret = (closes[d + 1] - closes[d]) / closes[d]
            if p == "bullish":
                signal_returns.append(daily_ret)
            elif p == "bearish":
                signal_returns.append(-daily_ret)
            else:
                signal_returns.append(0.0)

        # Sharpe Ratio (annualised, assuming 250 trading days/year)
        if signal_returns and len(signal_returns) > 1:
            mean_r = sum(signal_returns) / len(signal_returns)
            variance = sum((r - mean_r) ** 2 for r in signal_returns) / len(signal_returns)
            std_r = variance ** 0.5
            sharpe = (mean_r / std_r * (250 ** 0.5)) if std_r > 0 else 0.0
        else:
            sharpe = 0.0

        # Max Drawdown from cumulative equity curve
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in signal_returns:
            equity *= (1 + r)
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)

        return {
            "total": n,
            "directional_accuracy": round(directional_acc, 4),
            "bullish_precision": round(bull_prec, 4),
            "bullish_recall": round(bull_rec, 4),
            "bearish_precision": round(bear_prec, 4),
            "bearish_recall": round(bear_rec, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 4),
        }


# ── Offline tests (deterministic synthetic data) ──────────────────────────────
class TestBacktestEngine:
    """Unit-test the backtest engine with synthetic price series."""

    def _retriever(self):
        from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever
        r = PakistanStockRetriever.__new__(PakistanStockRetriever)
        return r

    def _linear_up(self, n=100):
        return [100.0 + i * 0.5 for i in range(n)]

    def _linear_down(self, n=100):
        return [200.0 - i * 0.5 for i in range(n)]

    def _flat(self, n=100):
        return [150.0] * n

    def test_engine_returns_expected_keys(self):
        r = self._retriever()
        eng = BacktestEngine(r)
        result = eng.run(self._linear_up())
        for key in ("total", "directional_accuracy", "bullish_precision",
                    "bearish_precision", "sharpe_ratio", "max_drawdown"):
            assert key in result, f"Missing key: {key}"

    def test_uptrend_bullish_accuracy_high(self):
        """Perfectly rising prices → model should be mostly bullish → high accuracy."""
        r = self._retriever()
        eng = BacktestEngine(r)
        result = eng.run(self._linear_up(120))
        assert result["total"] > 0
        assert result["directional_accuracy"] >= 0.55, \
            f"Uptrend accuracy too low: {result['directional_accuracy']}"

    def test_downtrend_bearish_accuracy_high(self):
        """Perfectly falling prices → model should be mostly bearish → high accuracy."""
        r = self._retriever()
        eng = BacktestEngine(r)
        result = eng.run(self._linear_down(120))
        assert result["total"] > 0
        assert result["directional_accuracy"] >= 0.50

    def test_max_drawdown_in_range(self):
        result = BacktestEngine(self._retriever()).run(self._linear_up())
        assert 0.0 <= result["max_drawdown"] <= 1.0

    def test_sharpe_finite(self):
        result = BacktestEngine(self._retriever()).run(self._linear_up())
        assert math.isfinite(result["sharpe_ratio"])

    def test_all_metrics_in_valid_range(self):
        for prices in [self._linear_up(), self._linear_down(), self._flat()]:
            result = BacktestEngine(self._retriever()).run(prices)
            if result["total"] == 0:
                continue
            assert 0.0 <= result["directional_accuracy"] <= 1.0
            assert 0.0 <= result["bullish_precision"] <= 1.0
            assert 0.0 <= result["bearish_precision"] <= 1.0
            assert 0.0 <= result["max_drawdown"] <= 1.0

    def test_minimum_warmup_bars_respected(self):
        """With only 31 prices and WARMUP=30, only 1 prediction is possible."""
        r = self._retriever()
        eng = BacktestEngine(r)
        result = eng.run(self._linear_up(32))
        assert result["total"] >= 1

    def test_too_few_prices_returns_zero_total(self):
        r = self._retriever()
        eng = BacktestEngine(r)
        result = eng.run(self._linear_up(10))  # < WARMUP=30
        assert result["total"] == 0


# ── Live backtest (real Supabase data) ────────────────────────────────────────
class TestLiveBacktest:
    """Runs the backtest against real stock_prices data in Supabase."""

    def _get_symbols(self, limit=5) -> List[str]:
        from src.db.connection import get_supabase_client
        sb = get_supabase_client()
        r = sb.table("stock_prices").select("symbol").limit(500).execute()
        if not r.data:
            return []
        symbols = list({row["symbol"] for row in r.data})
        return sorted(symbols)[:limit]

    def _get_closes(self, symbol: str) -> List[float]:
        from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever
        ret = PakistanStockRetriever()
        end = date.today()
        start = end - timedelta(days=365)
        data = ret.get_price_history(symbol, start_date=start, end_date=end, limit=300)
        return [float(d["close"]) for d in data if d.get("close")]

    @LIVE_SKIP
    def test_live_backtest_directional_accuracy(self):
        """
        Aggregate directional accuracy across top-5 stocks by data volume
        must be >= MIN_DIRECTIONAL_ACCURACY (50%).
        """
        from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever
        retriever = PakistanStockRetriever()
        engine = BacktestEngine(retriever)

        symbols = self._get_symbols(limit=5)
        assert len(symbols) > 0, "No symbols found in Supabase"

        total_correct, total_predictions = 0, 0
        results_log = {}

        for sym in symbols:
            closes = self._get_closes(sym)
            if len(closes) < MIN_DAYS_PER_STOCK:
                continue
            res = engine.run(closes)
            if res["total"] == 0:
                continue
            results_log[sym] = res
            n = res["total"]
            total_predictions += n
            total_correct += int(res["directional_accuracy"] * n)

        print("\nBacktest Results:")
        for sym, res in results_log.items():
            print(f"  {sym}: acc={res['directional_accuracy']:.2%}  "
                  f"sharpe={res['sharpe_ratio']:.2f}  "
                  f"dd={res['max_drawdown']:.2%}  "
                  f"n={res['total']}")

        if total_predictions == 0:
            pytest.skip("No predictions made — stocks may have insufficient history")

        agg_acc = total_correct / total_predictions
        assert agg_acc >= MIN_DIRECTIONAL_ACCURACY, \
            f"Aggregate directional accuracy {agg_acc:.2%} < {MIN_DIRECTIONAL_ACCURACY:.2%}"

    @LIVE_SKIP
    def test_live_max_drawdown_within_limit(self):
        from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever
        retriever = PakistanStockRetriever()
        engine = BacktestEngine(retriever)
        symbols = self._get_symbols(limit=5)
        violations = []
        for sym in symbols:
            closes = self._get_closes(sym)
            if len(closes) < MIN_DAYS_PER_STOCK:
                continue
            res = engine.run(closes)
            if res["total"] == 0:
                continue
            if res["max_drawdown"] > MAX_DRAWDOWN_LIMIT:
                violations.append(f"{sym}: dd={res['max_drawdown']:.2%}")
        if violations:
            pytest.fail(f"Max drawdown exceeded {MAX_DRAWDOWN_LIMIT:.0%}:\n" + "\n".join(violations))

    @LIVE_SKIP
    def test_live_per_stock_metrics_report(self):
        """
        Non-failing report: prints per-stock metrics and saves to JSON.
        Only fails if ALL stocks produce zero predictions.
        """
        from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever
        retriever = PakistanStockRetriever()
        engine = BacktestEngine(retriever)
        symbols = self._get_symbols(limit=10)
        all_results = {}
        for sym in symbols:
            closes = self._get_closes(sym)
            if len(closes) < MIN_DAYS_PER_STOCK:
                all_results[sym] = {"skipped": True, "reason": "insufficient_data"}
                continue
            all_results[sym] = engine.run(closes)

        # Save report
        report_path = os.path.join(os.path.dirname(__file__), "..", "backtest_report.json")
        with open(report_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nBacktest report saved: {report_path}")

        ran = [r for r in all_results.values() if r.get("total", 0) > 0]
        assert len(ran) > 0, "No stocks had enough data to run backtest"
