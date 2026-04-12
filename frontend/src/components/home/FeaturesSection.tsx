/**
 * FeaturesSection — 3×2 grid of feature cards with icons.
 */
import { motion } from 'framer-motion';
import {
  TrendingUp,
  BookOpen,
  Building2,
  Database,
  Lightbulb,
  ShieldCheck,
} from 'lucide-react';

const features = [
  {
    icon: TrendingUp,
    title: 'PSX Stock Analysis',
    desc: 'Deep-dive into any listed Pakistani company: historical performance, trend analysis, and AI-generated investment insights.',
  },
  {
    icon: BookOpen,
    title: 'Theory & Explainability',
    desc: 'Ask any finance or economics concept and get a structured, paragraph-level explanation with clickable reference links.',
  },
  {
    icon: Building2,
    title: 'SBP & NBP Data',
    desc: 'Query monetary policy decisions, interest rates, currency reserves, and national bank data in plain language.',
  },
  {
    icon: Database,
    title: 'RAG-Powered Answers',
    desc: 'Every answer first checks our indexed Supabase and Qdrant databases before calling external models — for grounded, cited responses.',
  },
  {
    icon: Lightbulb,
    title: 'Investment Opinion',
    desc: 'Get an AI opinion on whether to invest in a stock, when to invest, and why — with reasoning and risk caveats.',
  },
  {
    icon: ShieldCheck,
    title: 'Explainable AI Accuracy Score',
    desc: 'Every answer comes with a confidence range (color-coded green/yellow/red) so you always know how much to trust the response.',
  },
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] } },
};

export default function FeaturesSection() {
  return (
    <section id="features" className="home-section features-section">
      <div className="home-section-inner">
        <h2 className="home-section-title">What Fintex Can Do For You</h2>

        <motion.div
          className="features-grid"
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
        >
          {features.map((f, i) => (
            <motion.div key={i} className="feature-card" variants={item}>
              <div className="feature-icon">
                <f.icon size={24} />
              </div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
