/**
 * Footer — Fintex site footer with links and attribution.
 */
import { Code } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="home-footer">
      <div className="home-footer-inner">
        <div className="footer-brand">
          <span className="fx-mono">FX</span>
          <span className="footer-wordmark">Fintex</span>
          <p className="footer-tagline">AI-Powered Finance Research Agent</p>
        </div>

        <nav className="footer-links">
          <a href="#hero">Home</a>
          <a href="#features">Features</a>
          <a href="#techniques">About</a>
          <a href="#">Privacy Policy</a>
          <a href="#">Terms</a>
        </nav>

        <div className="footer-right">
          <p className="footer-fyp">Built as part of FYP</p>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="footer-github">
            <Code size={18} />
          </a>
        </div>
      </div>

      <div className="footer-bottom">
        © 2025 Fintex. All rights reserved.
      </div>
    </footer>
  );
}
