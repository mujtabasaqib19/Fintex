/**
 * AnsweringTechniques — Three-column layout explaining RAG, multi-source, and scoring.
 */
import { motion } from 'framer-motion';
import { BrainCircuit, Network, Gauge } from 'lucide-react';

const techniques = [
  {
    icon: BrainCircuit,
    title: 'Context-Aware RAG',
    desc: 'Fintex uses Retrieval-Augmented Generation. Before calling any external model, it semantically searches your indexed financial knowledge base in Qdrant. Questions are embedded with Ollama and matched against stored chunks. This means answers are grounded in verified financial data, not hallucinated.',
  },
  {
    icon: Network,
    title: 'Multi-Source Orchestration',
    desc: 'If Qdrant returns a match AND Supabase has a prior answer, Fintex merges both sources and generates a synthesized, more detailed answer. If only one source has data, it uses that. If neither has data, it falls back to FinGPT, and as a last resort, Google Gemini API.',
  },
  {
    icon: Gauge,
    title: 'Explainable Confidence Scoring',
    desc: 'Every answer includes an accuracy range. 80–100% = green (high confidence, both databases had relevant data). 50–79% = yellow (one source or partial match). Below 50% = red (external model only, limited grounding).',
  },
];

export default function AnsweringTechniques() {
  return (
    <section id="techniques" className="home-section techniques-section">
      <div className="home-section-inner">
        <h2 className="home-section-title">Built for Financial Intelligence</h2>

        <div className="techniques-grid">
          {techniques.map((t, i) => (
            <motion.div
              key={i}
              className="technique-card"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="technique-icon"><t.icon size={28} /></div>
              <h3 className="technique-title">{t.title}</h3>
              <p className="technique-desc">{t.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
