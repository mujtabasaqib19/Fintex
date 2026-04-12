/**
 * OptimizeButton — AI prompt optimization (✨ Optimize).
 * Calls backend with mode: "optimize" to rewrite the user's query.
 */
import { useState } from 'react';
import { Sparkles } from 'lucide-react';

interface Props {
  inputText: string;
  onOptimized: (text: string) => void;
}

export default function OptimizeButton({ inputText, onOptimized }: Props) {
  const [loading, setLoading] = useState(false);

  if (!inputText.trim()) return null;

  const handleOptimize = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: inputText,
          mode: 'optimize',
          use_reasoning: false,
          format: 'brief',
        }),
      });
      const data = await res.json();
      const optimized = data.answer?.answer || data.optimized || inputText;
      onOptimized(optimized);
    } catch {
      console.error('Optimization failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      className="optimize-btn"
      onClick={handleOptimize}
      disabled={loading}
      title="Let AI clean up your question"
    >
      <Sparkles size={14} />
      <span>{loading ? 'Optimizing...' : 'Optimize'}</span>
    </button>
  );
}
