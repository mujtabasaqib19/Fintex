import { useState } from 'react';
import { searchDocuments, type SearchResult } from '../api';

const SECTORS = [
  '', 'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
  'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
  'real_estate', 'stocks',
];

const SOURCE_TYPES = [
  '', 'news_article', 'breaking_update', 'deep_dive', 'policy_document',
  'industry_report', 'earnings_release', 'regulatory_filing',
  'research_paper', 'market_commentary', 'press_release',
];

export default function Search() {
  const [query, setQuery] = useState('');
  const [sector, setSector] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const res = await searchDocuments(query, 10, sector || undefined, sourceType || undefined);
      setResults(res.results);
    } catch (err) {
      console.error('Search error:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const formatLabel = (s: string) => s.replace(/_/g, ' ');
  const truncate = (s: string, n: number) => (s.length > n ? s.slice(0, n) + '...' : s);

  return (
    <div>
      <div className="page-header animate-in">
        <h2>Search</h2>
        <p>Vector similarity search across all ingested documents</p>
      </div>

      {/* ── Search Form ── */}
      <form onSubmit={handleSearch} className="animate-in stagger-1">
        <div style={{ display: 'flex', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
          <input
            className="form-input"
            type="text"
            placeholder="Search for economic data, news, reports..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
            {loading ? <span className="spinner" /> : '◇'}
            Search
          </button>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
          <select className="form-select" value={sector} onChange={e => setSector(e.target.value)} style={{ width: 200 }}>
            <option value="">All Sectors</option>
            {SECTORS.filter(Boolean).map(s => <option key={s} value={s}>{formatLabel(s)}</option>)}
          </select>
          <select className="form-select" value={sourceType} onChange={e => setSourceType(e.target.value)} style={{ width: 200 }}>
            <option value="">All Source Types</option>
            {SOURCE_TYPES.filter(Boolean).map(t => <option key={t} value={t}>{formatLabel(t)}</option>)}
          </select>
        </div>
      </form>

      {/* ── Results ── */}
      <div className="card animate-in stagger-2" style={{ marginTop: 'var(--space-xl)', padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div className="skeleton" style={{ height: 300 }} />
        ) : !searched ? (
          <div className="empty-state">
            <div className="empty-state-icon">◇</div>
            <h3>Enter a search query</h3>
            <p>Search uses vector similarity to find relevant documents</p>
          </div>
        ) : results.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">∅</div>
            <h3>No results found</h3>
            <p>Try adjusting your query or removing filters</p>
          </div>
        ) : (
          <>
            <div style={{ padding: 'var(--space-md) var(--space-lg)', borderBottom: '1px solid var(--border-subtle)' }}>
              <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {results.length} RESULT{results.length !== 1 ? 'S' : ''}
              </span>
            </div>
            {results.map((r, i) => (
              <div key={r.id} className={`search-result animate-in stagger-${Math.min(i + 1, 6)}`}>
                <div className="result-title">{r.title || 'Untitled'}</div>
                <div className="result-content">{truncate(r.content || '', 200)}</div>
                <div className="result-meta">
                  <span className="badge badge-blue">{formatLabel(r.source_type || '')}</span>
                  <span className="badge badge-gold">{formatLabel(r.sector_category || '')}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                    <div className="score-bar">
                      <div className="score-bar-fill" style={{ width: `${Math.round(r.similarity * 100)}%` }} />
                    </div>
                    <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--accent-gold)' }}>
                      {(r.similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                  {r.url && (
                    <a href={r.url} target="_blank" rel="noreferrer" style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>
                      🔗 Source
                    </a>
                  )}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
