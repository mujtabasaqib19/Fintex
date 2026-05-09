import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import { getPSXMarketActivity, type PSXMarketActivity } from '../../api';

export default function MarketStatus() {
  const [data, setData] = useState<PSXMarketActivity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMarket = async () => {
      try {
        const res = await getPSXMarketActivity();
        setData(res);
      } catch (e) {
        console.error('Failed to fetch market data', e);
      } finally {
        setLoading(false);
      }
    };
    fetchMarket();
    // Refresh every 5 minutes
    const timer = setInterval(fetchMarket, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <div className="sidebar-market-loading">
        <div className="skeleton-line" style={{ width: '80%' }} />
        <div className="skeleton-line" style={{ width: '60%' }} />
      </div>
    );
  }

  if (!data) return null;

  const isUp = data.change >= 0;
  const isZero = data.change === 0;

  return (
    <div className="sidebar-market-status">
      <div className="market-status-header">
        <Activity size={14} className="text-muted" />
        <span className="market-status-title">PSX KSE-100</span>
      </div>
      <div className="market-status-main">
        <div className="market-index">
          {data.current_index?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        </div>
        <div className={`market-change ${isUp ? 'positive' : 'negative'} ${isZero ? 'neutral' : ''}`}>
          {isZero ? (
            <Minus size={14} />
          ) : isUp ? (
            <TrendingUp size={14} />
          ) : (
            <TrendingDown size={14} />
          )}
          <span>
            {Math.abs(data.change).toFixed(2)} ({Math.abs(data.percent_change).toFixed(2)}%)
          </span>
        </div>
      </div>
      <div className="market-status-footer">
        Vol: {(data.volume / 1_000_000).toFixed(1)}M shares
      </div>
    </div>
  );
}
