import { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts';
import {
  getPSXMarketActivity, getPSXFullBoard, getPSXAnnouncements,
} from '../api';
import type { PSXMarketActivity, PSXSectorGroup, PSXAnnouncements } from '../api';

// ─── Custom Tooltip ────────────────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="psx-tooltip">
      <div className="psx-tooltip-date">{label}</div>
      <div className="psx-tooltip-row"><span>Index</span><span>{d.index?.toLocaleString()}</span></div>
      <div className="psx-tooltip-row"><span>Vol.</span><span>{(d.volume / 1_000_000).toFixed(1)}M</span></div>
      <div className={`psx-tooltip-row ${d.change >= 0 ? 'bull' : 'bear'}`}>
        <span>Chg.</span><span>{d.change >= 0 ? '+' : ''}{d.change?.toFixed(2)}</span>
      </div>
    </div>
  );
};

// ─── helpers ────────────────────────────────────────────────────────────────
const fmt = (n: number) => n?.toLocaleString(undefined, { maximumFractionDigits: 2 });
const fmtVol = (n: number) => {
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(2) + 'B';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  return n?.toLocaleString();
};

// ─── Component ──────────────────────────────────────────────────────────────
export default function MarketSummary() {
  const [activity, setActivity] = useState<PSXMarketActivity | null>(null);
  const [board, setBoard]       = useState<PSXSectorGroup[]>([]);
  const [announcements, setAnnouncements] = useState<PSXAnnouncements | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = useCallback(async () => {
    try {
      setError(null);
      const [act, brd, ann] = await Promise.all([
        getPSXMarketActivity(),
        getPSXFullBoard(),
        getPSXAnnouncements(),
      ]);
      setActivity(act);
      setBoard(brd.sectors);
      setAnnouncements(ann);
      setLastRefresh(new Date());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000); // refresh every 60s
    return () => clearInterval(id);
  }, [load]);

  const bullish = (activity?.change ?? 0) >= 0;

  return (
    <div className="psx-page">
      {/* ── Page Header ─────────────────────────────────────────────── */}
      <div className="page-header">
        <div>
          <h2 className="page-title">PSX Market Summary</h2>
          <p className="page-subtitle">
            Pakistan Stock Exchange — KSE-100 Index&nbsp;
            <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>
              Last refresh: {lastRefresh.toLocaleTimeString()}
            </span>
          </p>
        </div>
        <button className="psx-refresh-btn" onClick={load} title="Refresh">⟳ Refresh</button>
      </div>

      {error && (
        <div className="psx-error">
          ⚠ {error} — showing cached / mock data
        </div>
      )}

      {loading ? (
        <div className="psx-loading">
          <div className="spinner" />
          <span>Fetching market data…</span>
        </div>
      ) : (
        <div className="psx-grid">

          {/* ── LEFT: Announcements ───────────────────────────────── */}
          <div className="psx-panel psx-announcements">
            <div className="psx-panel-header">
              <span className="psx-panel-icon">📢</span>
              PSX ANNOUNCEMENTS (NOTICES)
              <span className="psx-view-all">View All ›</span>
            </div>
            <div className="psx-ann-list">
              {announcements?.exchange_announcements.map((a, i) => (
                <div key={i} className="psx-ann-item">
                  <div className="psx-ann-ts">{a.timestamp}</div>
                  <div className="psx-ann-msg">
                    <span className="psx-ann-tag exchange">EXCHANGE</span>
                    {a.message}
                  </div>
                </div>
              ))}
            </div>

            <div className="psx-panel-header" style={{ marginTop: '1rem' }}>
              <span className="psx-panel-icon">🏢</span>
              COMPANY ANNOUNCEMENTS
            </div>
            <div className="psx-ann-list">
              {announcements?.company_announcements.map((a, i) => (
                <div key={i} className="psx-ann-item">
                  <div className="psx-ann-ts">{a.timestamp}</div>
                  <div className="psx-ann-msg">
                    <span className="psx-ann-tag company">{a.symbol}</span>
                    {a.message}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── CENTER: Chart + Highlights ────────────────────────── */}
          <div className="psx-center">

            {/* Index badge */}
            <div className="psx-index-badge">
              <div className="psx-index-label">KSE 100 Index</div>
              <div className="psx-index-value">{fmt(activity?.current_index ?? 0)}</div>
              <div className={`psx-index-change ${bullish ? 'bull' : 'bear'}`}>
                {bullish ? '▲' : '▼'} {Math.abs(activity?.change ?? 0).toFixed(2)}
                &nbsp;({Math.abs(activity?.percent_change ?? 0).toFixed(2)}%)
              </div>
            </div>

            {/* Area Chart */}
            <div className="psx-chart-wrap">
              <div className="psx-chart-title">
                <span className={bullish ? 'bull' : 'bear'}>{bullish ? '↗' : '↘'} Market Activity</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={activity?.history ?? []} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="kseGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor={bullish ? '#22c55e' : '#ef4444'} stopOpacity={0.35} />
                      <stop offset="95%" stopColor={bullish ? '#22c55e' : '#ef4444'} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis
                    tick={{ fill: '#6b7280', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => (v / 1000).toFixed(0) + 'k'}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip content={<ChartTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="index"
                    stroke={bullish ? '#22c55e' : '#ef4444'}
                    strokeWidth={2}
                    fill="url(#kseGrad)"
                    dot={false}
                    activeDot={{ r: 4, fill: bullish ? '#22c55e' : '#ef4444', strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Market Highlights */}
            <div className="psx-highlights">
              <div className="psx-highlights-title">MARKET HIGHLIGHTS</div>
              <div className="psx-highlights-grid">
                <div className="psx-hl-row">
                  <span>Market Status</span>
                  <span className={bullish ? 'bull' : 'bear'}>
                    {new Date().getHours() >= 9 && new Date().getHours() < 15 ? 'Open' : 'Closed'}
                  </span>
                </div>
                <div className="psx-hl-row">
                  <span>Current Index</span>
                  <span>{fmt(activity?.current_index ?? 0)}</span>
                </div>
                <div className="psx-hl-row">
                  <span>Change</span>
                  <span className={bullish ? 'bull' : 'bear'}>
                    {bullish ? '+' : ''}{activity?.change?.toFixed(2)}
                  </span>
                </div>
                <div className="psx-hl-row">
                  <span>% Change</span>
                  <span className={bullish ? 'bull' : 'bear'}>
                    {bullish ? '+' : ''}{activity?.percent_change?.toFixed(2)}%
                  </span>
                </div>
                <div className="psx-hl-row">
                  <span>High</span>
                  <span className="bull">{fmt(activity?.high ?? 0)}</span>
                </div>
                <div className="psx-hl-row">
                  <span>Low</span>
                  <span className="bear">{fmt(activity?.low ?? 0)}</span>
                </div>
                <div className="psx-hl-row">
                  <span>Volume</span>
                  <span>{fmtVol(activity?.volume ?? 0)}</span>
                </div>
                {activity?.previous_close && (
                  <div className="psx-hl-row">
                    <span>Previous Close</span>
                    <span>{fmt(activity.previous_close)}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── RIGHT: Main Board / Recent Quotes ─────────────────── */}
          <div className="psx-panel psx-board">
            <div className="psx-panel-header">
              <span className="psx-panel-icon">📊</span>
              FULL MARKET BOARD
            </div>
            
            <div style={{ maxHeight: '780px', overflowY: 'auto' }}>
              {board.map((sector) => (
                <div key={sector.sector} style={{ marginBottom: '1rem' }}>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: 'var(--bg-elevated)', 
                    color: '#e2e8f0', 
                    fontWeight: 600, 
                    fontSize: '0.75rem', 
                    letterSpacing: '0.05em',
                    borderTop: '1px solid var(--border-subtle)',
                    borderBottom: '1px solid var(--border-subtle)'
                  }}>
                    {sector.sector}
                  </div>
                  <table className="psx-table">
                    <thead>
                      <tr>
                        <th>SCRIP</th>
                        <th>LDCP</th>
                        <th>OPEN</th>
                        <th>HIGH</th>
                        <th>LOW</th>
                        <th>CURRENT</th>
                        <th>CHANGE</th>
                        <th>VOLUME</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sector.scrips.map((s) => (
                        <tr key={s.symbol} className={s.bull ? 'row-bull' : 'row-bear'}>
                          <td className="scrip-name" style={{ width: '22%' }}>{s.symbol}</td>
                          <td>{s.ldcp.toFixed(2)}</td>
                          <td>{s.open.toFixed(2)}</td>
                          <td className="bull">{s.high.toFixed(2)}</td>
                          <td className="bear">{s.low.toFixed(2)}</td>
                          <td style={{ fontWeight: 600 }}>{s.current.toFixed(2)}</td>
                          <td className={s.bull ? 'bull' : 'bear'} style={{ fontWeight: 600 }}>
                            {s.bull ? '▲ ' : '▼ '}{Math.abs(s.change).toFixed(2)}
                          </td>
                          <td className="vol-cell">{fmtVol(s.volume)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
