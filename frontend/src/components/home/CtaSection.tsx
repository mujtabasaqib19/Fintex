/**
 * CtaSection — Bottom-of-page call to action.
 */
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export default function CtaSection() {
  return (
    <section className="cta-section">
      <motion.div
        className="cta-content"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <h2 className="cta-title">Ready to research smarter?</h2>
        <p className="cta-sub">
          Join thousands of users exploring Pakistan's financial landscape with AI.
        </p>
        <Link to="/login" className="btn btn-primary cta-btn">
          Create Free Account <ArrowRight size={16} />
        </Link>
      </motion.div>
    </section>
  );
}
