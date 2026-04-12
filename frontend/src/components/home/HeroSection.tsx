/**
 * HeroSection — Full-viewport hero with headline, CTAs, and animated mockup.
 */
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ChevronDown } from 'lucide-react';

export default function HeroSection() {
  const scrollToHowItWorks = () => {
    document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section id="hero" className="hero-section">
      <div className="hero-bg-mesh" />

      <div className="hero-content">
        {/* Left */}
        <motion.div
          className="hero-left"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="hero-headline">
            <span>Pakistan's First</span>
            <span className="hero-headline-accent">AI Finance Research Agent</span>
          </h1>
          <p className="hero-subheadline">
            Ask anything about PSX stocks, State Bank of Pakistan data, macroeconomic
            trends, and more — powered by real-time financial intelligence.
          </p>
          <div className="hero-ctas">
            <Link to="/login" className="btn btn-primary hero-btn-primary">
              Start Researching <ArrowRight size={16} />
            </Link>
            <button className="btn hero-btn-secondary" onClick={scrollToHowItWorks}>
              See How It Works <ChevronDown size={16} />
            </button>
          </div>
        </motion.div>

        {/* Right — Chat mockup */}
        <motion.div
          className="hero-right"
          initial={{ opacity: 0, x: 60 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="hero-mockup">
            <div className="hero-mockup-glow" />
            <div className="hero-mockup-window">
              <div className="hero-mockup-bar">
                <span /><span /><span />
              </div>
              <div className="hero-mockup-chat">
                <div className="mockup-msg mockup-user">
                  <p>What is the current trend for OGDC on PSX?</p>
                </div>
                <div className="mockup-msg mockup-ai">
                  <p><strong>OGDC (Oil & Gas Development Company)</strong> is currently trading at PKR 265.60, showing a <span className="accent-text">+2.4% uptick</span> this week...</p>
                  <div className="mockup-badge">Accuracy: 87–93%</div>
                </div>
                <div className="mockup-msg mockup-user">
                  <p>Should I invest in OGDC right now?</p>
                </div>
                <div className="mockup-typing">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
