import { useState } from 'react';
import { ingestUrl, ingestText } from '../api';

const SOURCE_TYPES = [
  'news_article', 'breaking_update', 'deep_dive', 'policy_document',
  'industry_report', 'earnings_release', 'regulatory_filing',
  'research_paper', 'market_commentary', 'press_release',
];

const SECTORS = [
  'banking', 'bonds', 'commodities', 'corporate_actions', 'currency_fx',
  'derivatives', 'economic_indicators', 'funds_etfs', 'insurance',
  'real_estate', 'stocks',
];

export default function Ingest() {
  const [tab, setTab] = useState<'url' | 'text'>('url');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  // URL form
  const [url, setUrl] = useState('');
  const [urlSourceType, setUrlSourceType] = useState('');
  const [urlSector, setUrlSector] = useState('');

  // Text form
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [textSourceType, setTextSourceType] = useState('news_article');
  const [textSector, setTextSector] = useState('');

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4000);
  };

  const handleUrlIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    try {
      const res = await ingestUrl(url, urlSourceType || undefined, urlSector || undefined);
      showToast('success', `✓ Ingested ${res.documents_created} document(s)`);
      setUrl('');
    } catch (err: unknown) {
      showToast('error', err instanceof Error ? err.message : 'Ingest failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTextIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    setLoading(true);
    try {
      const res = await ingestText(title, content, textSourceType, textSector || undefined);
      showToast('success', `✓ Ingested ${res.documents_created} document(s)`);
      setTitle('');
      setContent('');
    } catch (err: unknown) {
      showToast('error', err instanceof Error ? err.message : 'Ingest failed');
    } finally {
      setLoading(false);
    }
  };

  const formatLabel = (s: string) => s.replace(/_/g, ' ');

  return (
    <div>
      <div className="page-header animate-in">
        <h2>Ingest Data</h2>
        <p>Add documents to the pipeline via URL or raw text</p>
      </div>

      {/* ── Tab Switcher ── */}
      <div className="format-switcher animate-in stagger-1" style={{ marginBottom: 'var(--space-xl)', width: 'fit-content' }}>
        <button className={`format-option ${tab === 'url' ? 'active' : ''}`} onClick={() => setTab('url')}>
          URL
        </button>
        <button className={`format-option ${tab === 'text' ? 'active' : ''}`} onClick={() => setTab('text')}>
          Raw Text
        </button>
      </div>

      <div className="card animate-in stagger-2" style={{ maxWidth: 640 }}>
        {tab === 'url' ? (
          <form onSubmit={handleUrlIngest}>
            <div className="form-group">
              <label className="form-label">URL to Ingest</label>
              <input
                className="form-input"
                type="url"
                placeholder="https://example.com/article or .pdf"
                value={url}
                onChange={e => setUrl(e.target.value)}
                required
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)' }}>
              <div className="form-group">
                <label className="form-label">Source Type (optional)</label>
                <select className="form-select" value={urlSourceType} onChange={e => setUrlSourceType(e.target.value)}>
                  <option value="">Auto-detect</option>
                  {SOURCE_TYPES.map(t => <option key={t} value={t}>{formatLabel(t)}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Sector (optional)</label>
                <select className="form-select" value={urlSector} onChange={e => setUrlSector(e.target.value)}>
                  <option value="">Auto-classify</option>
                  {SECTORS.map(s => <option key={s} value={s}>{formatLabel(s)}</option>)}
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !url.trim()}>
              {loading ? <><span className="spinner" /> Ingesting...</> : '◆ Ingest URL'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleTextIngest}>
            <div className="form-group">
              <label className="form-label">Title</label>
              <input
                className="form-input"
                type="text"
                placeholder="Document title"
                value={title}
                onChange={e => setTitle(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Content</label>
              <textarea
                className="form-textarea"
                placeholder="Paste your text content here..."
                value={content}
                onChange={e => setContent(e.target.value)}
                required
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)' }}>
              <div className="form-group">
                <label className="form-label">Source Type</label>
                <select className="form-select" value={textSourceType} onChange={e => setTextSourceType(e.target.value)}>
                  {SOURCE_TYPES.map(t => <option key={t} value={t}>{formatLabel(t)}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Sector (optional)</label>
                <select className="form-select" value={textSector} onChange={e => setTextSector(e.target.value)}>
                  <option value="">Auto-classify</option>
                  {SECTORS.map(s => <option key={s} value={s}>{formatLabel(s)}</option>)}
                </select>
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading || !title.trim() || !content.trim()}>
              {loading ? <><span className="spinner" /> Ingesting...</> : '◆ Ingest Text'}
            </button>
          </form>
        )}
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
