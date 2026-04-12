/**
 * HomePage — Landing page container with all sections.
 */
import Navbar from '../components/home/Navbar';
import HeroSection from '../components/home/HeroSection';
import StatsBar from '../components/home/StatsBar';
import FeaturesSection from '../components/home/FeaturesSection';
import HowItWorks from '../components/home/HowItWorks';
import AnsweringTechniques from '../components/home/AnsweringTechniques';
import CtaSection from '../components/home/CtaSection';
import Footer from '../components/home/Footer';

export default function HomePage() {
  return (
    <div className="home-page">
      <Navbar />
      <HeroSection />
      <StatsBar />
      <FeaturesSection />
      <HowItWorks />
      <AnsweringTechniques />
      <CtaSection />
      <Footer />
    </div>
  );
}
