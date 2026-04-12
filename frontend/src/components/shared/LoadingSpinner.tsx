/**
 * LoadingSpinner — Shared loading component.
 */
export default function LoadingSpinner({ text }: { text?: string }) {
  return (
    <div className="loading-screen">
      <div className="loading-logo">
        <span className="fx-mono">FX</span>
      </div>
      <div className="spinner" style={{ width: 28, height: 28 }} />
      {text && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 12 }}>{text}</p>}
    </div>
  );
}
