/**
 * HowItWorks — Three-step horizontal timeline.
 */
import { motion } from 'framer-motion';
import { MessageSquare, Search, BarChart3 } from 'lucide-react';

const steps = [
  {
    step: 1,
    icon: MessageSquare,
    title: 'You Ask',
    desc: 'You type a question — a stock query, a macro question, or a theory request. Fintex reads your intent and prepares to search.',
  },
  {
    step: 2,
    icon: Search,
    title: 'We Search',
    desc: "Fintex searches Supabase and Qdrant first. If a grounded answer exists, it's retrieved and enriched. If not, FinGPT is called. Google API steps in only as a last resort.",
  },
  {
    step: 3,
    icon: BarChart3,
    title: 'You Get Intel',
    desc: 'A structured, professional answer is returned — with sources, accuracy score, visual charts (for stocks), and optionally an investment opinion.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="home-section hiw-section">
      <div className="home-section-inner">
        <h2 className="home-section-title">How Fintex Answers Your Questions</h2>

        <div className="hiw-timeline">
          {steps.map((s, i) => (
            <motion.div
              key={s.step}
              className="hiw-step"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="hiw-badge">{s.step}</div>
              <div className="hiw-icon"><s.icon size={28} /></div>
              <h3 className="hiw-title">{s.title}</h3>
              <p className="hiw-desc">{s.desc}</p>

              {/* Connecting line (except last) */}
              {i < steps.length - 1 && <div className="hiw-connector" />}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
