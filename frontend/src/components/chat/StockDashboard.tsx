/**
 * StockDashboard — Section 7 full implementation.
 * Renders Company Background Card, Period Summary Strip,
 * 4 interactive Recharts (Close Price, High/Low Band, Volume, Daily % Change),
 * Timeframe Selector, and Investment Opinion Block.
 *
 * All data comes from the /api/stock/query backend endpoint which
 * queries the real public.stock_prices Supabase table.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell, Legend,
} from 'recharts';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { fetchStockQuery, fetchStockFundamentals, createStockAlert, type StockQueryResponse, type StockDataPoint, type StockFundamental } from '../../api';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Info, ChevronDown, ChevronUp, FileText, Bell, History, Activity } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

type Timeframe = '1W' | '1M' | '3M' | '6M' | '1Y' | '3Y' | 'All';

interface Props {
  ticker: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FORMATTERS
// ─────────────────────────────────────────────────────────────────────────────

function fmtPKR(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return 'N/A';
  return `PKR ${Number(n).toLocaleString('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtVol(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return 'N/A';
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function fmtDate(raw: string, tf: Timeframe): string {
  if (!raw) return '';
  const d = new Date(raw);
  if (tf === '1W' || tf === '1M') return d.toLocaleDateString('en-PK', { month: 'short', day: 'numeric' });
  if (tf === '3M' || tf === '6M') return d.toLocaleDateString('en-PK', { month: 'short', day: 'numeric' });
  if (tf === '1Y') return d.toLocaleDateString('en-PK', { month: 'short', year: '2-digit' });
  return d.toLocaleDateString('en-PK', { year: 'numeric', month: 'short' });
}

// ─────────────────────────────────────────────────────────────────────────────
// TIMEFRAME → DATE RANGE
// ─────────────────────────────────────────────────────────────────────────────

function timeframeToRange(tf: Timeframe): { startDate: string; endDate: string } {
  const today = new Date();
  const end = today.toISOString().split('T')[0];
  const start = new Date(today);
  switch (tf) {
    case '1W': start.setDate(start.getDate() - 7); break;
    case '1M': start.setDate(start.getDate() - 30); break;
    case '3M': start.setDate(start.getDate() - 90); break;
    case '6M': start.setDate(start.getDate() - 180); break;
    case '1Y': start.setFullYear(start.getFullYear() - 1); break;
    case '3Y': start.setFullYear(start.getFullYear() - 3); break;
    case 'All': start.setFullYear(2020, 0, 1); break;
  }
  return { startDate: start.toISOString().split('T')[0], endDate: end };
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPANY METADATA (local knowledge base — augmented by backend data)
// ─────────────────────────────────────────────────────────────────────────────

const COMPANY_META: Record<string, { name: string; sector: string; listed: string; hq: string; desc: string }> = {
  ENGRO:  { name: 'Engro Corporation Limited', sector: 'Fertilizers / Conglomerates', listed: '1965', hq: 'Karachi', desc: 'Engro Corporation is one of Pakistan\'s largest conglomerates with core businesses in fertilizers, food, energy, and petrochemicals. It is listed on the Pakistan Stock Exchange (PSX) and is a subsidiary of Dawood Hercules Corporation.' },
  HBL:    { name: 'Habib Bank Limited', sector: 'Commercial Banking', listed: '1947', hq: 'Karachi', desc: 'Pakistan\'s largest private bank with a global network spanning over 25 countries. HBL offers retail, corporate, consumer, and Islamic banking services with the widest branch network in the country.' },
  UBL:    { name: 'United Bank Limited', sector: 'Commercial Banking', listed: '1959', hq: 'Karachi', desc: 'One of Pakistan\'s leading commercial banks, providing retail, corporate, and investment banking services. UBL has a strong presence in the Middle East and is known for its innovative digital banking initiatives.' },
  MCB:    { name: 'MCB Bank Limited', sector: 'Commercial Banking', listed: '1947', hq: 'Lahore', desc: 'MCB Bank is one of Pakistan\'s oldest and most well-capitalised banks. It delivers a comprehensive range of financial services to individuals and businesses across Pakistan and internationally.' },
  MEBL:   { name: 'Meezan Bank Limited', sector: 'Islamic Banking', listed: '2002', hq: 'Karachi', desc: 'Pakistan\'s first and largest dedicated Islamic bank, offering Shariah-compliant banking products across retail, corporate, trade, and treasury sectors.' },
  OGDC:   { name: 'Oil & Gas Development Company Limited', sector: 'Oil & Gas Exploration', listed: '1997', hq: 'Islamabad', desc: 'The largest oil and gas exploration and production company in Pakistan, majority state-owned. OGDC contributes significantly to Pakistan\'s domestic energy security.' },
  PPL:    { name: 'Pakistan Petroleum Limited', sector: 'Oil & Gas Exploration', listed: '1955', hq: 'Karachi', desc: 'PPL is a major oil and gas exploration company in Pakistan, responsible for producing a significant share of the country\'s natural gas. It operates multiple gas fields across Sindh and Balochistan.' },
  MARI:   { name: 'Mari Petroleum Company Limited', sector: 'Oil & Gas Exploration', listed: '1994', hq: 'Islamabad', desc: 'One of Pakistan\'s top natural gas producers operating the Mari Gas Field, one of the largest in the country. MARI consistently delivers strong dividends and has high free cash flow generation.' },
  LUCK:   { name: 'Lucky Cement Limited', sector: 'Cement', listed: '1996', hq: 'Karachi', desc: 'Pakistan\'s largest cement manufacturer with plants across the country. Lucky Cement also has international operations in Iraq and the DR Congo, and a diversified portfolio through Lucky Core Industries.' },
  FCCL:   { name: 'Fauji Cement Company Limited', sector: 'Cement', listed: '1993', hq: 'Rawalpindi', desc: 'A leading cement producer sponsored by the Fauji Foundation. FCCL operates one of the largest single-stream cement plants in Pakistan and benefits from strong institutional backing.' },
  TRG:    { name: 'TRG Pakistan Limited', sector: 'Technology & Communications', listed: '2003', hq: 'Karachi', desc: 'TRG Pakistan is a technology investment company with a portfolio of global BPO and technology businesses. Its investments include Ibex Global, a leading customer engagement services company.' },
  SYS:    { name: 'Systems Limited', sector: 'Technology & Communications', listed: '2000', hq: 'Lahore', desc: 'Pakistan\'s leading IT company providing enterprise software, digital transformation, and IT outsourcing services. SYS has a strong US and European clientele and continues to expand globally.' },
  HUBC:   { name: 'Hub Power Company Limited', sector: 'Power Generation', listed: '1997', hq: 'Karachi', desc: 'One of Pakistan\'s first and largest independent power producers, operating gas-fired, coal, and wind power plants. HUBC supplies a significant chunk of Pakistan\'s national grid capacity.' },
  KAPCO:  { name: 'Kot Addu Power Company Limited', sector: 'Power Generation', listed: '1996', hq: 'Muzaffargarh', desc: 'A major thermal power plant operator in Pakistan generating electricity for the national grid. KAPCO is known for regular dividend payouts and is partially government-owned.' },
  KEL:    { name: 'K-Electric Limited', sector: 'Power Distribution', listed: '1913', hq: 'Karachi', desc: 'The sole electricity provider for Karachi and surrounding areas, serving millions of customers. K-Electric operates generation, transmission, and distribution assets in an integrated model.' },
  NESTLE: { name: 'Nestlé Pakistan Limited', sector: 'Food & Beverages', listed: '1980', hq: 'Lahore', desc: 'A subsidiary of the global FMCG giant Nestlé S.A., producing a wide range of food and beverage products in Pakistan including Milo, Nescafé, Nestlé Pure Life water, and dairy products.' },
  FFC:    { name: 'Fauji Fertilizer Company Limited', sector: 'Fertilizers', listed: '1979', hq: 'Rawalpindi', desc: 'Pakistan\'s largest urea producer, sponsored by the Fauji Foundation. FFC consistently delivers high dividend yields and benefits from subsidized feedstock, making it a defensive income stock.' },
  FATIMA: { name: 'Fatima Fertilizer Company Limited', sector: 'Fertilizers', listed: '2012', hq: 'Lahore', desc: 'One of Pakistan\'s newest and most modern fertilizer manufacturers producing urea, CAN, and nitric acid. Fatima benefits from low-cost gas supply and modern production facilities.' },
  BOP:    { name: 'The Bank of Punjab', sector: 'Commercial Banking', listed: '1989', hq: 'Lahore', desc: 'A large provincial commercial bank headquartered in Lahore, Punjab. BOP serves retail, SME, and corporate clients across Pakistan with a growing network of branches and digital services.' },
  NBP:    { name: 'National Bank of Pakistan', sector: 'Commercial Banking (State)', listed: '1949', hq: 'Karachi', desc: 'Pakistan\'s largest state-owned commercial bank, acting as fiscal agent for the government. NBP provides commercial, investment, and retail banking services across Pakistan and internationally.' },
};

function getCompanyMeta(symbol: string) {
  return COMPANY_META[symbol.toUpperCase()] || {
    name: `${symbol.toUpperCase()} — PSX Listed Company`,
    sector: 'Pakistan Stock Exchange',
    listed: 'N/A',
    hq: 'Pakistan',
    desc: 'This company is listed on the Pakistan Stock Exchange (PSX). Detailed company background is not available in the local knowledge base for this ticker.',
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// CHART TOOLTIP STYLES
// ─────────────────────────────────────────────────────────────────────────────

const tooltipStyle = {
  background: 'var(--bg-surface, #1a2035)',
  border: '1px solid var(--border-subtle, #2a3555)',
  borderRadius: 10,
  fontSize: 12,
  color: 'var(--text-primary, #e2e8f0)',
  boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
};

const axisStyle = { fill: 'var(--text-muted, #718096)', fontSize: 11 };

// ─────────────────────────────────────────────────────────────────────────────
// CHART INFO TOOLTIP
// ─────────────────────────────────────────────────────────────────────────────

function ChartInfoIcon({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="chart-info-icon" style={{ position: 'relative', cursor: 'pointer' }}
      onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
      <Info size={13} style={{ color: 'var(--text-muted)', verticalAlign: 'middle' }} />
      {show && (
        <span style={{
          position: 'absolute', top: '120%', right: 0, zIndex: 100,
          background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
          borderRadius: 8, padding: '6px 10px', fontSize: 11,
          color: 'var(--text-secondary)', width: 200, whiteSpace: 'normal',
          boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
        }}>{text}</span>
      )}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function StockDashboard({ ticker }: Props) {
  const [timeframe, setTimeframe] = useState<Timeframe>('1Y');
  const [stockData, setStockData] = useState<StockQueryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opinionExpanded, setOpinionExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState<'technical' | 'fundamental'>('technical');
  const [fundamentals, setFundamentals] = useState<StockFundamental[]>([]);
  const [loadingFunds, setLoadingFunds] = useState(false);

  const downloadPDF = async () => {
    const element = document.getElementById(`stock-report-${ticker}`);
    if (!element) return;
    
    // Switch to technical tab to ensure charts are visible if needed
    // or just capture current view.
    
    const canvas = await html2canvas(element, { scale: 2, backgroundColor: '#0A0C10' });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    const imgProps = pdf.getImageProperties(imgData);
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
    
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save(`Fintex_Report_${ticker.toUpperCase()}_${new Date().toISOString().split('T')[0]}.pdf`);
  };

  const loadFundamentals = useCallback(async () => {
    setLoadingFunds(true);
    try {
      const res = await fetchStockFundamentals(ticker);
      setFundamentals(res.data);
    } catch (e) {
      console.error('Failed to load fundamentals', e);
    } finally {
      setLoadingFunds(false);
    }
  }, [ticker]);

  useEffect(() => {
    if (activeTab === 'fundamental') loadFundamentals();
  }, [activeTab, loadFundamentals]);

  const loadData = useCallback(async (tf: Timeframe) => {
    setLoading(true);
    setError(null);
    try {
      const { startDate, endDate } = timeframeToRange(tf);
      const res = await fetchStockQuery(ticker, startDate, endDate);
      setStockData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load stock data');
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => { loadData(timeframe); }, [loadData, timeframe]);

  const meta = getCompanyMeta(ticker);

  // ── Prepare chart-friendly data (filter zero close) ──
  const chartPoints: (StockDataPoint & { displayDate: string })[] =
    (stockData?.data || [])
      .filter(d => d.close > 0)
      .map(d => ({ ...d, displayDate: fmtDate(d.date, timeframe) }));

  const stats = stockData?.stats;
  const avail = stockData?.availability;
  const hasZeroRows = stockData?.has_zero_rows ?? false;

  // ── Volume availability check ──
  const hasVolume = chartPoints.some(d => (d.volume ?? 0) > 0);

  // ── Sentiment ──
  const sentiment = stats
    ? (stats.change_pct >= 5 ? 'bullish' : stats.change_pct <= -5 ? 'bearish' : 'neutral')
    : 'neutral';

  // ── Support / Resistance ──
  const support = stockData?.support_level;
  const resistance = stockData?.resistance_level;

  // ─────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────

  return (
    <div className="stock-dashboard" id={`stock-report-${ticker}`}>
      {/* ── Dashboard Header Actions ── */}
      <div className="stock-dashboard-actions">
        <div className="dashboard-tabs">
          <button 
            className={`tab-btn ${activeTab === 'technical' ? 'active' : ''}`}
            onClick={() => setActiveTab('technical')}
          >
            <Activity size={14} /> Technical Analysis
          </button>
          <button 
            className={`tab-btn ${activeTab === 'fundamental' ? 'active' : ''}`}
            onClick={() => setActiveTab('fundamental')}
          >
            <History size={14} /> Fundamental Health
          </button>
        </div>
        <div className="dashboard-tools">
          <button className="tool-btn btn-alert" title="Set Price Alert">
            <Bell size={14} /> Monitor Price
          </button>
          <button className="tool-btn btn-pdf" onClick={downloadPDF} title="Export Analysis to PDF">
            <FileText size={14} /> Download PDF Report
          </button>
        </div>
      </div>

      {/* ── 2.1 Company Background Card ── */}
      <div className="stock-company-card">
        <div className="stock-company-card-accent" />
        <div className="stock-company-card-body">
          <div className="stock-company-header">
            <div>
              <h2 className="stock-company-name">{meta.name}</h2>
              <div className="stock-company-meta-row">
                <span className="stock-ticker-badge">{ticker.toUpperCase()}</span>
                <span className="stock-meta-pill">🏭 {meta.sector}</span>
                <span className="stock-meta-pill">🏙 {meta.hq}</span>
                <span className="stock-meta-pill">📅 Listed {meta.listed}</span>
              </div>
            </div>
            {avail && (
              <div className="stock-avail-chip">
                📅 Data: {avail.earliest_date} → {avail.latest_date}
                &nbsp;|&nbsp;
                {avail.total_records?.toLocaleString()} trading days
              </div>
            )}
          </div>
          <p className="stock-company-desc">{meta.desc}</p>
        </div>
      </div>

      {/* ── Data Quality Notice ── */}
      {hasZeroRows && (
        <div className="stock-data-warning">
          <AlertTriangle size={14} />
          <span>
            Some trading days in this period have incomplete open/high/low data (recorded as 0.00).
            These points have been excluded from chart rendering and calculations.
            <strong> Close prices remain the primary metric.</strong>
          </span>
        </div>
      )}

      {/* ── No Data Notice ── */}
      {!loading && !error && chartPoints.length === 0 && (
        <div className="stock-no-data">
          <Info size={16} />
          <span>No data found for <strong>{ticker.toUpperCase()}</strong> in the selected period.
            Try a different timeframe or verify the symbol is listed on PSX.</span>
        </div>
      )}

      {/* ── 2.2 Period Summary Strip ── */}
      {stats && !loading && (
        <div className="stock-summary-strip">
          <div className="summary-chip">
            <span className="chip-label">📈 Period High</span>
            <span className="chip-value">{fmtPKR(stats.period_high)}</span>
          </div>
          <div className="summary-chip">
            <span className="chip-label">📉 Period Low</span>
            <span className="chip-value">{fmtPKR(stats.period_low)}</span>
          </div>
          <div className="summary-chip">
            <span className="chip-label">📊 Avg Close</span>
            <span className="chip-value">{fmtPKR(stats.avg_close)}</span>
          </div>
          <div className="summary-chip">
            <span className="chip-label">🔁 Volume</span>
            <span className="chip-value">{fmtVol(stats.total_volume)} shares</span>
          </div>
          <div className="summary-chip">
            <span className="chip-label">📅 Start Price</span>
            <span className="chip-value">{fmtPKR(stats.start_price)}</span>
          </div>
          <div className="summary-chip">
            <span className="chip-label">🏁 End Price</span>
            <span className="chip-value">{fmtPKR(stats.end_price)}</span>
          </div>
          <div className={`summary-chip chip-change ${stats.change_pct >= 0 ? 'positive' : 'negative'}`}>
            <span className="chip-label">↕️ Overall Change</span>
            <span className="chip-value chip-change-val">
              {stats.change_pct >= 0 ? '+' : ''}{stats.change_pct?.toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* ── 2.3 Timeframe Selector (Only for Technical) ── */}
      {activeTab === 'technical' && (
        <div className="stock-timeframe-bar">
          {(['1W', '1M', '3M', '6M', '1Y', '3Y', 'All'] as Timeframe[]).map(tf => (
            <button
              key={tf}
              className={`tf-btn ${timeframe === tf ? 'active' : ''}`}
              onClick={() => { setTimeframe(tf); }}
              id={`stock-tf-${tf}`}
            >
              {tf}
            </button>
          ))}
        </div>
      )}

      {activeTab === 'fundamental' && (
        <div className="stock-fundamental-panel">
          <div className="stock-chart-title">
            <span>🛡️ Strategic Fundamental Health</span>
            <ChartInfoIcon text="Multi-year financial metrics representing the absolute fiscal strength and valuation ratios of the company." />
          </div>
          
          {loadingFunds ? (
             <div className="stock-loading"><div className="stock-spinner" /></div>
          ) : fundamentals.length > 0 ? (
            <div className="fundamental-table-wrapper">
              <table className="fundamental-table">
                <thead>
                  <tr>
                    <th>Fiscal Year</th>
                    <th>Revenue</th>
                    <th>Net Profit</th>
                    <th>EPS</th>
                    <th>P/E Ratio</th>
                    <th>Div. Yield</th>
                    <th>Market Cap</th>
                  </tr>
                </thead>
                <tbody>
                  {fundamentals.map(f => (
                    <tr key={f.fiscal_year}>
                      <td><strong>{f.fiscal_year}</strong></td>
                      <td>{fmtVol(f.revenue)}</td>
                      <td>{fmtVol(f.net_profit)}</td>
                      <td>{f.eps?.toFixed(2)}</td>
                      <td>{f.pe_ratio?.toFixed(1)}x</td>
                      <td>{f.dividend_yield?.toFixed(2)}%</td>
                      <td>{fmtVol(f.market_cap)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
             <div className="stock-no-data">
                <Info size={16} /> <span>No fundamental historical data found for {ticker.toUpperCase()}.</span>
             </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="stock-loading">
          <div className="stock-spinner" />
          <span>Loading {ticker.toUpperCase()} market data...</span>
        </div>
      ) : error ? (
        <div className="stock-error">
          <AlertTriangle size={16} /> {error}
        </div>
      ) : (activeTab === 'technical' && chartPoints.length > 0) ? (
        <div className="stock-charts-block">

          {/* ── Chart A: Close Price Line Chart ── */}
          <div className="stock-chart-panel">
            <div className="stock-chart-title">
              <span>📈 Close Price (PKR)</span>
              <ChartInfoIcon text="Daily closing price for this stock. Teal line with gradient fill. Dashed line shows the period average close." />
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartPoints} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#00D4AA" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle,#2a3555)" vertical={false} />
                <XAxis dataKey="displayDate" tick={axisStyle} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={axisStyle} axisLine={false} tickLine={false} domain={['auto', 'auto']}
                  tickFormatter={v => `${(v / 1000).toFixed(0)}K`} />
                <Tooltip contentStyle={tooltipStyle}
                  formatter={(v: number) => [fmtPKR(v), 'Close']}
                  labelFormatter={l => `📅 ${l}`} />
                {stats?.avg_close && (
                  <ReferenceLine y={stats.avg_close} stroke="#00D4AA" strokeDasharray="6 3"
                    label={{ value: 'Avg', fill: '#00D4AA', fontSize: 10 }} />
                )}
                <Area type="monotone" dataKey="close" stroke="#00D4AA" strokeWidth={2}
                  fill={`url(#grad-${ticker})`} dot={false}
                  activeDot={{ r: 5, fill: '#00D4AA', stroke: '#fff', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* ── Chart B: High / Low Range Band ── */}
          {chartPoints.some(d => (d.high ?? 0) > 0 && (d.low ?? 0) > 0) && (
            <div className="stock-chart-panel">
              <div className="stock-chart-title">
                <span>📊 Daily High / Low Range</span>
                <ChartInfoIcon text="Green area shows the intraday high, red area shows the intraday low. The spread between them visualises daily price volatility." />
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={chartPoints} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`high-grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#22C55E" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#22C55E" stopOpacity={0.03} />
                    </linearGradient>
                    <linearGradient id={`low-grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#EF4444" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#EF4444" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle,#2a3555)" vertical={false} />
                  <XAxis dataKey="displayDate" tick={axisStyle} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={axisStyle} axisLine={false} tickLine={false} domain={['auto', 'auto']}
                    tickFormatter={v => `${(v / 1000).toFixed(0)}K`} />
                  <Tooltip contentStyle={tooltipStyle}
                    formatter={(v: number, name: string) => [fmtPKR(v), name === 'high' ? '🟢 High' : '🔴 Low']}
                    labelFormatter={l => `📅 ${l}`} />
                  <Legend formatter={v => v === 'high' ? '🟢 High' : '🔴 Low'} />
                  <Area type="monotone" dataKey="high" stroke="#22C55E" strokeWidth={1.5}
                    fill={`url(#high-grad-${ticker})`} dot={false}
                    activeDot={{ r: 4 }} />
                  <Area type="monotone" dataKey="low" stroke="#EF4444" strokeWidth={1.5}
                    fill={`url(#low-grad-${ticker})`} dot={false}
                    activeDot={{ r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ── Chart C: Volume Bar Chart ── */}
          {hasVolume ? (
            <div className="stock-chart-panel">
              <div className="stock-chart-title">
                <span>📦 Trading Volume</span>
                <ChartInfoIcon text="Number of shares traded each day. Higher volume bars often coincide with significant price moves or news events." />
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartPoints} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle,#2a3555)" vertical={false} />
                  <XAxis dataKey="displayDate" tick={axisStyle} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={axisStyle} axisLine={false} tickLine={false} tickFormatter={fmtVol} />
                  <Tooltip contentStyle={tooltipStyle}
                    formatter={(v: number) => [fmtVol(v), 'Volume']}
                    labelFormatter={l => `📅 ${l}`} />
                  <Bar dataKey="volume" fill="#6366F1" opacity={0.75} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="stock-chart-panel stock-chart-unavailable">
              <Info size={14} />
              <span>Volume data not available for this symbol in the selected period.</span>
            </div>
          )}

          {/* ── Chart D: Daily % Change Bars ── */}
          {chartPoints.some(d => d.daily_change_pct != null) && (
            <div className="stock-chart-panel">
              <div className="stock-chart-title">
                <span>📉 Daily Price Change (%)</span>
                <ChartInfoIcon text="Percentage change between opening and closing price each day. Green = price gained, Red = price fell." />
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartPoints} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle,#2a3555)" vertical={false} />
                  <XAxis dataKey="displayDate" tick={axisStyle} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tick={axisStyle} axisLine={false} tickLine={false}
                    tickFormatter={v => `${v}%`} />
                  <Tooltip contentStyle={tooltipStyle}
                    formatter={(v: number) => [`${Number(v).toFixed(2)}%`, 'Daily Change']}
                    labelFormatter={l => `📅 ${l}`} />
                  <ReferenceLine y={0} stroke="var(--border-subtle,#2a3555)" strokeDasharray="4 2" />
                  <Bar dataKey="daily_change_pct" radius={[2, 2, 0, 0]}>
                    {chartPoints.map((entry, i) => (
                      <Cell key={i}
                        fill={(entry.daily_change_pct ?? 0) >= 0 ? '#22C55E' : '#EF4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

        </div>
      ) : null}

      {/* ── 2.5 Investment Opinion Block ── */}
      {stats && !loading && (
        <div className="stock-opinion-block">
          <button
            className="stock-opinion-header"
            onClick={() => setOpinionExpanded(v => !v)}
            id="stock-opinion-toggle"
          >
            <div className="opinion-header-left">
              {sentiment === 'bullish' ? <TrendingUp size={15} color="#22C55E" /> :
               sentiment === 'bearish' ? <TrendingDown size={15} color="#EF4444" /> :
               <Minus size={15} color="#EAB308" />}
              <span className="opinion-title">🧠 Fintex Investment Opinion</span>
              <span className="opinion-ticker-badge">{ticker.toUpperCase()}</span>
              <span className="opinion-ai-badge">AI-Generated Opinion</span>
            </div>
            {opinionExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {opinionExpanded && (
            <div className="stock-opinion-body">
              <div className="opinion-disclaimer-top">
                <AlertTriangle size={12} />
                <span><strong>Not financial advice.</strong> For educational purposes only. Consult a licensed financial advisor.</span>
              </div>

              {/* Part 1 — Sentiment */}
              <div className="opinion-section">
                <div className={`sentiment-badge sentiment-${sentiment}`}>
                  {sentiment === 'bullish' ? '🟢 Bullish' : sentiment === 'bearish' ? '🔴 Bearish' : '🟡 Neutral'}
                </div>
                <p className="opinion-text">
                  As of <strong>{avail?.latest_date || 'the latest available date'}</strong>,{' '}
                  <strong>{ticker.toUpperCase()}</strong> closed at{' '}
                  <strong>{fmtPKR(stats.end_price)}</strong>, representing a{' '}
                  <strong className={stats.change_pct >= 0 ? 'text-green' : 'text-red'}>
                    {stats.change_pct >= 0 ? '+' : ''}{stats.change_pct?.toFixed(2)}%
                  </strong>{' '}
                  move over the selected period from{' '}
                  <strong>{fmtPKR(stats.start_price)}</strong>.{' '}
                  The current trend is <strong>{sentiment.toUpperCase()}</strong> based on price momentum analysis.
                </p>
              </div>

              {/* Part 2 — Reasons to Consider */}
              <div className="opinion-section">
                <h4 className="opinion-section-title text-green">✅ Reasons to Consider</h4>
                <ul className="opinion-bullets">
                  {stats.change_pct > 0 && <li>Positive momentum: +{stats.change_pct.toFixed(2)}% return over the selected period.</li>}
                  <li>Close price (<strong>{fmtPKR(stats.end_price)}</strong>) vs. period average (<strong>{fmtPKR(stats.avg_close)}</strong>) provides a mean-reversion anchor.</li>
                  <li>Sector: <strong>{meta.sector}</strong> — evaluate macro tailwinds for this sector in Pakistan's current economic cycle.</li>
                  {stats.end_price < stats.avg_close && <li>Currently trading below period average — potential undervaluation relative to recent history.</li>}
                  <li>Pakistan's ongoing macroeconomic stabilisation and SBP rate-cut cycle (2024–2025) may provide a supportive environment for equity re-rating.</li>
                </ul>
              </div>

              {/* Part 3 — Reasons to be Cautious */}
              <div className="opinion-section">
                <h4 className="opinion-section-title text-red">⚠️ Reasons to be Cautious</h4>
                <ul className="opinion-bullets">
                  {stats.change_pct < 0 && <li>Negative price momentum over the period ({stats.change_pct.toFixed(2)}%) — check for catalysts before entry.</li>}
                  {stats.period_high && stats.period_low && (
                    <li>
                      High intraday spread: Period High {fmtPKR(stats.period_high)} vs. Low {fmtPKR(stats.period_low)} indicates elevated volatility.
                    </li>
                  )}
                  <li>PKR depreciation risk and geopolitical uncertainty remain key macro headwinds for Pakistani equities.</li>
                  <li>Energy cost increases and inflationary pressures in Pakistan may compress margins for non-financial sectors.</li>
                  {!hasVolume && <li>Volume data is limited — this may indicate low liquidity and wide bid-ask spreads, increasing transaction risk.</li>}
                </ul>
              </div>

              {/* Part 4 — Suggested Entry */}
              {support && (
                <div className="opinion-section">
                  <h4 className="opinion-section-title">🎯 Suggested Entry Zone</h4>
                  <p className="opinion-text">
                    Based on historical price behavior over the selected period, a potential support zone exists around{' '}
                    <strong className="text-teal">{fmtPKR(support)}</strong>
                    {' '}(average of the lowest 10% of close prices). A possible entry could be near this level, particularly
                    if the SBP signals further rate cuts or the stock retraces to its period average of{' '}
                    <strong>{fmtPKR(stats.avg_close)}</strong>.
                  </p>
                </div>
              )}

              {/* Part 5 — Suggested Exit */}
              {resistance && (
                <div className="opinion-section">
                  <h4 className="opinion-section-title">🚀 Suggested Exit / Target</h4>
                  <p className="opinion-text">
                    The resistance zone around{' '}
                    <strong className="text-teal">{fmtPKR(resistance)}</strong>
                    {' '}(average of the highest 10% of close prices) has historically acted as a price ceiling.
                    A conservative price target for the next 6–12 months, assuming current macro conditions hold, could
                    be PKR {resistance.toFixed(2)}, representing a{' '}
                    <strong>
                      {stats.end_price > 0 && resistance != null ? ((resistance - stats.end_price) / stats.end_price * 100).toFixed(1) : '?'}%
                    </strong>{' '}
                    upside from current levels.
                  </p>
                </div>
              )}

            </div>
          )}
        </div>
      )}

    </div>
  );
}
