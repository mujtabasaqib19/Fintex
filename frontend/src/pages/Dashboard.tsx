/**
 * Dashboard — Redesigned with Fintex luxury-minimalist design system.
 * Features animated stat cards, sector grid, recent activity table.
 * Scoped to logged-in user context.
 */
import { useEffect, useState } from 'react';
import { getSectors, getRecentActivity, type SectorInfo, type RecentDoc } from '../api';
import {
  Database, TrendingUp, BarChart3, Activity,
  FileText, Clock, ArrowUpRight, ArrowDownRight
} from 'lucide-react';

export default function Dashboard() {
  const [sectors, setSectors] = useState<SectorInfo[]>([]);
  const [recent, setRecent] = useState<RecentDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [secRes, recRes] = await Promise.all([getSectors(), getRecentActivity(15)]);
        setSectors(secRes.sectors);
        setRecent(recRes.recent_documents);
      } catch (e) {
        console.error('Dashboard load error:', e);
        setError('Unable to load dashboard data. Backend may be offline.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const totalDocs = sectors.reduce((s, x) => s + x.document_count, 0);
  const totalSeries = sectors.reduce((s, x) => s + x.series_count, 0);
  const activeSectors = sectors.filter(s => s.document_count > 0 || s.series_count > 0).length;

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  const formatSectorName = (s: string) =>
    s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  const sectorIcons: Record<string, string> = {
    banking: '🏦', stocks: '📈', bonds: '📜', commodities: '⛏️',
    currency_fx: '💱', economic_indicators: '📊', insurance: '🛡️',
    real_estate: '🏠', funds_etfs: '📦', derivatives: '📉',
    corporate_actions: '🏢',
  };

  return (
    <div className="dashboard-page">
      {/* ── Header ── */}
      <div className="dashboard-header">
        <div>
          <h2 className="dashboard-title">Dashboard</h2>
          <p className="dashboard-subtitle">Real-time overview of your data pipeline</p>
        </div>
        <div className="dashboard-header-badge">
          <Activity size={14} />
          <span>Live</span>
        </div>
      </div>

      {error && (
        <div className="dashboard-error">
          <span>⚠</span> {error}
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div className="dashboard-stats">
        <div className="dash-stat-card">
          <div className="dash-stat-icon-wrap" style={{ background: 'rgba(0, 212, 170, 0.1)' }}>
            <Database size={20} style={{ color: 'var(--accent)' }} />
          </div>
          <div className="dash-stat-content">
            <span className="dash-stat-label">Total Documents</span>
            <span className="dash-stat-value">{loading ? '—' : totalDocs.toLocaleString()}</span>
          </div>
          <div className="dash-stat-trend up">
            <ArrowUpRight size={12} /> Active
          </div>
        </div>

        <div className="dash-stat-card">
          <div className="dash-stat-icon-wrap" style={{ background: 'rgba(34, 197, 94, 0.1)' }}>
            <TrendingUp size={20} style={{ color: '#22C55E' }} />
          </div>
          <div className="dash-stat-content">
            <span className="dash-stat-label">Time Series</span>
            <span className="dash-stat-value">{loading ? '—' : totalSeries.toLocaleString()}</span>
          </div>
          <div className="dash-stat-trend up">
            <ArrowUpRight size={12} /> Indexed
          </div>
        </div>

        <div className="dash-stat-card">
          <div className="dash-stat-icon-wrap" style={{ background: 'rgba(234, 179, 8, 0.1)' }}>
            <BarChart3 size={20} style={{ color: '#EAB308' }} />
          </div>
          <div className="dash-stat-content">
            <span className="dash-stat-label">Active Sectors</span>
            <span className="dash-stat-value">{loading ? '—' : `${activeSectors} / 11`}</span>
          </div>
          <div className="dash-stat-trend neutral">
            <Activity size={12} /> Tracked
          </div>
        </div>
      </div>

      {/* ── Sector Grid ── */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h3>Sector Overview</h3>
          <span className="dashboard-section-badge">{sectors.length} sectors</span>
        </div>
        <div className="dashboard-sector-grid">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="dash-sector-card skeleton" />
              ))
            : sectors.map((sec) => (
                <div key={sec.sector} className="dash-sector-card">
                  <div className="dash-sector-top">
                    <span className="dash-sector-icon">
                      {sectorIcons[sec.sector] || '📋'}
                    </span>
                    <span className="dash-sector-name">
                      {formatSectorName(sec.sector)}
                    </span>
                  </div>
                  <div className="dash-sector-bottom">
                    <div className="dash-sector-metric">
                      <FileText size={12} />
                      <span>{sec.document_count}</span>
                      <span className="metric-label">docs</span>
                    </div>
                    <div className="dash-sector-metric">
                      <TrendingUp size={12} />
                      <span>{sec.series_count}</span>
                      <span className="metric-label">series</span>
                    </div>
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* ── Recent Activity ── */}
      <div className="dashboard-section">
        <div className="dashboard-section-header">
          <h3>Recent Activity</h3>
          <span className="dashboard-section-badge">
            <Clock size={12} /> Last 15
          </span>
        </div>
        <div className="dashboard-table-wrap">
          {loading ? (
            <div className="skeleton" style={{ height: 300, borderRadius: 12 }} />
          ) : recent.length === 0 ? (
            <div className="dashboard-empty">
              <div className="dashboard-empty-icon">◇</div>
              <h4>No Recent Documents</h4>
              <p>Ingest some data to see activity here</p>
            </div>
          ) : (
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Sector</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recent.map(doc => (
                  <tr key={doc.id}>
                    <td className="dashboard-table-title">
                      {doc.title || 'Untitled'}
                    </td>
                    <td>
                      <span className="dash-badge type">
                        {doc.source_type?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="dash-badge sector">
                        {formatSectorName(doc.sector_category || '—')}
                      </span>
                    </td>
                    <td className="dashboard-table-time">
                      {doc.ingested_at ? formatTime(doc.ingested_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
