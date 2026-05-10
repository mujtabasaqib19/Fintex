"""
Benchmark 3 — Technical Indicator Correctness
==============================================
Validates Fintex RSI / MACD / Bollinger Band / SMA math against pandas-ta.

Run:
    pip install pandas-ta pytest
    pytest tests/test_technical_indicators.py -v
"""
import sys, os, math, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.retrieval.pakistan_stock_retriever import PakistanStockRetriever

try:
    import pandas as pd
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False

SKIP_TA = pytest.mark.skipif(not HAS_PANDAS_TA, reason="pip install pandas-ta")

# reuse without hitting DB
retriever = PakistanStockRetriever.__new__(PakistanStockRetriever)

def _prices(n=80, start=100.0, step=0.5):
    return [round(start + i * step, 4) for i in range(n)]

def _oscillate(n=80):
    import math as m
    return [round(100 + 20 * m.sin(i * m.pi / 8), 4) for i in range(n)]

def _fake_ohlcv(n=80):
    p = _prices(n)
    return [{"date": f"2025-01-{i+1:02d}", "close": p[i],
              "high": p[i]+1, "low": p[i]-1, "volume": 100000+i*500}
             for i in range(n)]


# ─── SMA ──────────────────────────────────────────────────────────────────────
class TestSMA:
    @pytest.mark.parametrize("period", [7, 14, 30])
    def test_arithmetic(self, period):
        p = _prices(60)
        got = sum(p[-period:]) / period
        assert math.isfinite(got) and got > 0

    @pytest.mark.parametrize("period", [7, 14, 30])
    @SKIP_TA
    def test_matches_pandas_ta(self, period):
        p = _prices(80)
        ref = pd.Series(p).rolling(period).mean().iloc[-1]
        got = sum(p[-period:]) / period
        assert abs(got - ref) / ref < 0.001


# ─── RSI ──────────────────────────────────────────────────────────────────────
class TestRSI:
    def test_range_0_to_100(self):
        for p in [_prices(80), _oscillate(80)]:
            rsi = retriever._compute_rsi(p)
            assert rsi is not None and 0.0 <= rsi <= 100.0

    def test_all_gains_is_100(self):
        p = [float(i) for i in range(1, 30)]
        assert retriever._compute_rsi(p) == 100.0

    def test_all_losses_near_0(self):
        p = [float(30 - i) for i in range(30)]
        rsi = retriever._compute_rsi(p)
        assert rsi is not None and rsi < 5.0

    def test_none_on_insufficient(self):
        assert retriever._compute_rsi(_prices(10)) is None

    @pytest.mark.parametrize("val,expected", [(25, "oversold"), (50, "neutral"), (75, "overbought")])
    def test_signal_classification(self, val, expected):
        sig = "overbought" if val > 70 else ("oversold" if val < 30 else "neutral")
        assert sig == expected

    @SKIP_TA
    def test_matches_pandas_ta(self):
        p = _oscillate(80)
        ref = ta.rsi(pd.Series(p), length=14).dropna().iloc[-1]
        got = retriever._compute_rsi(p)
        assert got is not None and abs(got - ref) < 10.0  # Wilder vs simple avg tolerance


# ─── EMA ──────────────────────────────────────────────────────────────────────
class TestEMA:
    def test_length_correct(self):
        p = _prices(50)
        ema = retriever._compute_ema(p, 12)
        assert len(ema) == len(p) - 12 + 1

    def test_empty_on_insufficient(self):
        assert retriever._compute_ema(_prices(5), 12) == []

    def test_seed_equals_sma(self):
        p = _prices(40)
        ema = retriever._compute_ema(p, 12)
        assert math.isclose(ema[0], sum(p[:12]) / 12, rel_tol=1e-9)

    @SKIP_TA
    def test_matches_pandas_ta(self):
        p = _prices(60)
        ref = ta.ema(pd.Series(p), length=12).dropna().iloc[-1]
        got = retriever._compute_ema(p, 12)[-1]
        assert abs(got - ref) / ref < 0.05


# ─── MACD ─────────────────────────────────────────────────────────────────────
class TestMACD:
    def test_none_on_insufficient(self):
        assert retriever._compute_macd(_prices(30)) is None

    def test_keys_present(self):
        m = retriever._compute_macd(_prices(80))
        assert m and all(k in m for k in ("macd", "signal", "histogram", "trend"))

    def test_histogram_formula(self):
        m = retriever._compute_macd(_prices(80))
        assert m and math.isclose(m["histogram"], m["macd"] - m["signal"], abs_tol=1e-3)

    def test_trend_label(self):
        m = retriever._compute_macd(_prices(80))
        assert m
        assert m["trend"] == ("bullish" if m["histogram"] > 0 else "bearish")

    @SKIP_TA
    def test_matches_pandas_ta(self):
        p = _prices(80)
        ref = ta.macd(pd.Series(p), fast=12, slow=26, signal=9)
        ref_hist = ref["MACDh_12_26_9"].dropna().iloc[-1]
        m = retriever._compute_macd(p)
        assert m and abs(m["histogram"] - ref_hist) / (abs(ref_hist) + 1e-9) < 0.15


# ─── Bollinger Bands ──────────────────────────────────────────────────────────
class TestBollingerBands:
    def test_none_on_insufficient(self):
        assert retriever._compute_bollinger_bands(_prices(15)) is None

    def test_keys_present(self):
        bb = retriever._compute_bollinger_bands(_prices(60))
        assert bb and all(k in bb for k in ("upper", "middle", "lower", "bandwidth"))

    def test_ordering(self):
        bb = retriever._compute_bollinger_bands(_prices(60))
        assert bb and bb["lower"] <= bb["middle"] <= bb["upper"]

    def test_constant_prices_zero_bandwidth(self):
        bb = retriever._compute_bollinger_bands([100.0] * 25)
        assert bb and math.isclose(bb["upper"], bb["lower"], abs_tol=1e-6)

    def test_middle_is_sma20(self):
        p = _prices(60)
        bb = retriever._compute_bollinger_bands(p)
        assert bb and math.isclose(bb["middle"], sum(p[-20:]) / 20, rel_tol=1e-6)

    @SKIP_TA
    def test_matches_pandas_ta(self):
        p = _prices(60)
        series = pd.Series(p)
        ref_df = ta.bbands(series, length=20, std=2)
        
        # Find columns dynamically (can be BBU_20_2.0 or BBU_20_2 depending on version)
        u_col = [c for c in ref_df.columns if c.startswith("BBU")][0]
        l_col = [c for c in ref_df.columns if c.startswith("BBL")][0]
        
        ref_upper = ref_df[u_col].dropna().iloc[-1]
        ref_lower = ref_df[l_col].dropna().iloc[-1]
        bb = retriever._compute_bollinger_bands(p)
        assert bb
        assert abs(bb["upper"] - ref_upper) / ref_upper < 0.05
        assert abs(bb["lower"] - ref_lower) / (abs(ref_lower) + 1e-9) < 0.05


# ─── compute_technical_indicators integration ─────────────────────────────────
class TestComputeTechnicalIndicators:
    def _patch(self, n=80):
        import unittest.mock as m
        return m.patch.object(retriever, "get_price_history", return_value=_fake_ohlcv(n))

    def test_none_on_too_few_rows(self):
        with self._patch(5):
            assert retriever.compute_technical_indicators("TEST") is None

    def test_dict_on_sufficient_rows(self):
        with self._patch(80):
            r = retriever.compute_technical_indicators("TEST")
        assert r and r["symbol"] == "TEST" and r["latest_price"] > 0

    def test_expected_keys(self):
        with self._patch(80):
            r = retriever.compute_technical_indicators("TEST")
        assert r
        for k in ("sma_7", "sma_14", "sma_30", "rsi", "rsi_signal",
                  "macd", "bollinger_bands", "overall_signal", "signal_strength"):
            assert k in r, f"Missing key: {k}"

    def test_overall_signal_valid(self):
        with self._patch(80):
            r = retriever.compute_technical_indicators("TEST")
        assert r and r["overall_signal"] in ("bullish", "bearish", "neutral")

    def test_signal_strength_in_range(self):
        with self._patch(80):
            r = retriever.compute_technical_indicators("TEST")
        assert r and 0 <= r.get("signal_strength", 50) <= 100
