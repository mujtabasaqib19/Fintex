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

  // Enhanced color thresholds per User Request (Strict 80%+ baseline)
  const colors = {
    dark_green:  { bg: '#166534', text: '#ffffff' }, // > 85%
    light_green: { bg: '#00D4AA', text: '#0A0C10' }, // 80 - 85%
    error:       { bg: '#EF4444', text: '#ffffff' },
  };

  const getTheme = () => {
    if (min > 85) return colors.dark_green;
    if (min >= 80) return colors.light_green;
    return colors.error;
  };
  const c = getTheme();

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
          Score based on the data provenance. Dark Green = Verified Multi-Source. Light Green = Advanced Logic / Real-time Web. (Minimum baseline: 80%)
        </div>
      )}
    </div>
  );
}
