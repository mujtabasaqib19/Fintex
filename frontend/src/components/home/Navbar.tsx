/**
 * Home Page Navbar — Sticky frosted glass with smooth scroll links.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import ThemeToggle from '../shared/ThemeToggle';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const scrollTo = (id: string) => {
    setMobileOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <header className={`home-nav ${scrolled ? 'home-nav--scrolled' : ''}`}>
      <div className="home-nav-inner">
        {/* Logo */}
        <Link to="/" className="home-nav-logo">
          <span className="fx-mono">FX</span>
          <span className="home-nav-wordmark">Fintex</span>
        </Link>

        {/* Desktop links */}
        <nav className="home-nav-links">
          <button onClick={() => scrollTo('hero')}>Home</button>
          <button onClick={() => scrollTo('features')}>Features</button>
          <button onClick={() => scrollTo('how-it-works')}>How It Works</button>
          <button onClick={() => scrollTo('techniques')}>About</button>
        </nav>

        {/* Right */}
        <div className="home-nav-right">
          <ThemeToggle />
          <Link to="/login" className="btn btn-primary btn-sm home-nav-cta">
            Get Started
          </Link>
          <button
            className="home-nav-hamburger"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="home-nav-mobile">
          <button onClick={() => scrollTo('hero')}>Home</button>
          <button onClick={() => scrollTo('features')}>Features</button>
          <button onClick={() => scrollTo('how-it-works')}>How It Works</button>
          <button onClick={() => scrollTo('techniques')}>About</button>
          <Link to="/login" onClick={() => setMobileOpen(false)}>Get Started</Link>
        </div>
      )}
    </header>
  );
}
