/**
 * StatsBar — Animated counters that count up when scrolled into view.
 */
import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';

const stats = [
  { value: 10000, suffix: '+', label: 'Financial Data Points Indexed' },
  { value: 500, suffix: '+', label: 'PSX Companies Tracked' },
  { value: 95, suffix: '%', label: 'Answer Relevance Score' },
  { value: 0, suffix: '', label: 'Real-Time SBP & NBP Data', isText: true, text: 'Real-Time' },
];

function useCountUp(target: number, enabled: boolean, duration = 2000) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let start = 0;
    const step = target / (duration / 16);
    const id = setInterval(() => {
      start += step;
      if (start >= target) {
        setCount(target);
        clearInterval(id);
      } else {
        setCount(Math.floor(start));
      }
    }, 16);
    return () => clearInterval(id);
  }, [enabled, target, duration]);
  return count;
}

export default function StatsBar() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 },
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="stats-bar" ref={ref}>
      <div className="stats-bar-inner">
        {stats.map((stat, i) => (
          <StatItem key={i} stat={stat} visible={visible} index={i} />
        ))}
      </div>
    </section>
  );
}

function StatItem({ stat, visible, index }: {
  stat: typeof stats[number];
  visible: boolean;
  index: number;
}) {
  const count = useCountUp(stat.value, visible);

  return (
    <motion.div
      className="stat-item"
      initial={{ opacity: 0, y: 20 }}
      animate={visible ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.1, duration: 0.6 }}
    >
      <div className="stat-item-value">
        {stat.isText ? stat.text : `${count.toLocaleString()}${stat.suffix}`}
      </div>
      <div className="stat-item-label">{stat.label}</div>
    </motion.div>
  );
}
