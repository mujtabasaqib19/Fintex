/**
 * AccuracyBadge — Color-coded confidence pill for each answer, plus source tag.
 */
import { useState } from 'react';

interface Props {
  min: number;
  max: number;
  sourceLabel?: string;
}

export default function AccuracyBadge({ min, max, sourceLabel }: Props) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Revised color thresholds per Section 6 UI Spec
  const level = min >= 80 ? 'high' : min >= 60 ? 'medium' : 'low';
  const colors = {
    high:   { bg: '#00D4AA', text: '#0A0C10' },  // Fintex Teal (Grounded)
    medium: { bg: '#EAB308', text: '#0A0C10' },  // Gold (Partially Grounded)
    low:    { bg: '#EF4444', text: '#fff' },     // Red (Generative)
  };
  const c = colors[level];

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
        [ Accuracy: {min}–{max}% ]
      </span>
      {sourceLabel && (
        <span className="source-tag" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {sourceLabel}
        </span>
      )}
      {showTooltip && (
        <div className="accuracy-tooltip" style={{ maxWidth: '280px', width: 'max-content' }}>
          Score based on how much of this answer came from verified financial databases. Green = highly grounded. Yellow = partially grounded. Red = external model only.
        </div>
      )}
    </div>
  );
}
