/**
 * AccuracyBadge — Color-coded confidence pill for each answer, plus source tag.
 *
 * Display rules (per spec):
 *   - 89–100%  → Green       #22C55E  — "Grounded in verified indexed data"
 *   - 78–88%   → Light green #EAB308  — "Partially grounded or model-generated"
 *   - anything below 78% is floored to the 78–88% light-green band for display,
 *     so the UI never shows a red/low-confidence tier to the end user.
 */
import { useState } from 'react';

interface Props {
  min: number;
  max: number;
  sourceLabel?: string;
}

const DARK_GREEN = { bg: '#166534', text: '#FFFFFF' };
const LIGHT_GREEN = { bg: '#86EFAC', text: '#0A0C10' };

export default function AccuracyBadge({ min, max, sourceLabel }: Props) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Floor everything below 78% to the 78–88% light-green band.
  // 78-88% is light green, anything >= 89% is dark green.
  const isHighGrounded = min >= 89;
  const displayMin = isHighGrounded ? min : 78;
  const displayMax = isHighGrounded ? max : 88;

  const c = isHighGrounded ? DARK_GREEN : LIGHT_GREEN;

  return (
    <div
      className="accuracy-badge-wrapper"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
    >
      <span
        className="accuracy-badge"
        style={{ background: c.bg, color: c.text }}
      >
        [ Accuracy: {displayMin}–{displayMax}% ]
      </span>
      {sourceLabel && (
        <span className="source-tag" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {sourceLabel}
        </span>
      )}
      {showTooltip && (
        <div className="accuracy-tooltip" style={{ maxWidth: '300px', width: 'max-content' }}>
          Score based on how much of this answer came from verified financial
          databases. Green = highly grounded in indexed data. Light green =
          partially grounded or model-generated context.
        </div>
      )}
    </div>
  );
}
