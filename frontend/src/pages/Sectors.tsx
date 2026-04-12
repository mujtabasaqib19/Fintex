import { useEffect, useState } from 'react';
import { getSectors, type SectorInfo } from '../api';

const SECTOR_ICONS: Record<string, string> = {
  banking: '🏦',
  bonds: '📜',
  commodities: '⛏',
  corporate_actions: '📋',
  currency_fx: '💱',
  derivatives: '📐',
  economic_indicators: '📊',
  funds_etfs: '💼',
  insurance: '🛡',
  real_estate: '🏗',
  stocks: '📈',
};

const SECTOR_DESCRIPTIONS: Record<string, string> = {
  banking: 'KIBOR, SBP rates, deposit & lending rates, interbank',
  bonds: 'PIBs, T-Bills, Sukuk, Ijara, fixed income',
  commodities: 'Cement, gold, oil, cotton, wheat, coal, clinker',
  corporate_actions: 'Dividends, splits, mergers, buybacks',
  currency_fx: 'USD/PKR, EUR/PKR, GBP/PKR, forex rates',
  derivatives: 'Futures, options, swaps, structured products',
  economic_indicators: 'CPI, GDP, inflation, trade balance, remittances',
  funds_etfs: 'Mutual funds, ETFs, pension funds',
  insurance: 'Life, general, health, reinsurance',
  real_estate: 'Property, construction, REIT',
  stocks: 'KSE-100, KSE-30, PSX equities, individual tickers',
};

export default function Sectors() {
  const [sectors, setSectors] = useState<SectorInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSectors()
      .then(res => setSectors(res.sectors))
      .catch(err => console.error('Sectors error:', err))
      .finally(() => setLoading(false));
  }, []);

  const totalDocs = sectors.reduce((s, x) => s + x.document_count, 0);
  const totalSeries = sectors.reduce((s, x) => s + x.series_count, 0);
  const formatName = (s: string) => s.replace(/_/g, ' ');

  return (
    <div>
      <div className="page-header animate-in">
        <h2>Sectors</h2>
        <p>Explore all 11 economic sector categories and their data</p>
      </div>

      {/* ── Summary ── */}
      <div style={{ display: 'flex', gap: 'var(--space-xl)', marginBottom: 'var(--space-2xl)' }} className="animate-in stagger-1">
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="stat-label">Total Sectors</div>
          <div className="stat-value">11</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="stat-label">Total Documents</div>
          <div className="stat-value">{loading ? '—' : totalDocs}</div>
        </div>
        <div className="card" style={{ flex: 1, textAlign: 'center' }}>
          <div className="stat-label">Total Series</div>
          <div className="stat-value">{loading ? '—' : totalSeries}</div>
        </div>
      </div>

      {/* ── Sector Grid ── */}
      <div className="card-grid">
        {loading
          ? Array.from({ length: 11 }).map((_, i) => (
              <div key={i} className="card skeleton" style={{ height: 140 }} />
            ))
          : sectors.map((sec, i) => (
              <div key={sec.sector} className={`card sector-card animate-in stagger-${Math.min(i + 1, 6)}`}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', marginBottom: 'var(--space-md)' }}>
                  <span style={{ fontSize: '1.5rem' }}>{SECTOR_ICONS[sec.sector] || '◈'}</span>
                  <div>
                    <div className="sector-name" style={{ marginBottom: 0 }}>{formatName(sec.sector)}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 2 }}>
                      {SECTOR_DESCRIPTIONS[sec.sector] || ''}
                    </div>
                  </div>
                </div>
                <div className="sector-stats">
                  <div className="sector-stat">
                    <span className="sector-stat-value">{sec.document_count}</span>
                    <span className="sector-stat-label">Documents</span>
                  </div>
                  <div className="sector-stat">
                    <span className="sector-stat-value">{sec.series_count}</span>
                    <span className="sector-stat-label">Series</span>
                  </div>
                </div>
                {/* ── Data density bar ── */}
                {totalDocs > 0 && (
                  <div style={{ marginTop: 'var(--space-md)' }}>
                    <div className="score-bar" style={{ width: '100%' }}>
                      <div
                        className="score-bar-fill"
                        style={{ width: `${Math.min((sec.document_count / Math.max(totalDocs / 3, 1)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
      </div>
    </div>
  );
}
