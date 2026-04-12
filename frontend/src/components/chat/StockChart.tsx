/**
 * StockChart — Recharts line chart for stock price visualization.
 */
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';

interface DataPoint {
  date: string;
  price: number;
  volume?: number;
}

interface Props {
  data: DataPoint[];
  ticker?: string;
}

export default function StockChart({ data, ticker }: Props) {
  if (!data || data.length === 0) return null;

  return (
    <div className="stock-chart-container">
      <div className="stock-chart-header">
        {ticker && <span className="stock-chart-ticker">{ticker}</span>}
        <span className="stock-chart-label">Price (PKR)</span>
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="stockGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#00D4AA" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border-subtle)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 8,
              fontSize: 13,
              color: 'var(--text-primary)',
            }}
            formatter={(value: any) => [`PKR ${Number(value).toLocaleString()}`, 'Price']}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="#00D4AA"
            strokeWidth={2}
            fill="url(#stockGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
