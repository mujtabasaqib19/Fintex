/**
 * App — Root component with routing, auth context, and theme.
 * Integrates the new Home Page, Login, and overhauled Chat page
 * while preserving existing Dashboard, Ingest, Search, Sectors, and MarketSummary pages.
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { checkHealth } from './api';
import { useAuthProvider, AuthContext } from './hooks/useAuth';
import { useTheme } from './hooks/useTheme';
import ProtectedRoute from './components/shared/ProtectedRoute';

// Pages
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import Dashboard from './pages/Dashboard';
import Ingest from './pages/Ingest';
import Search from './pages/Search';
import Sectors from './pages/Sectors';
import MarketSummary from './pages/MarketSummary';
import SettingsPage from './pages/SettingsPage';

import './index.css';
import './psx.css';

function AppInner() {
  const auth = useAuthProvider();
  const { theme } = useTheme();
  const [online, setOnline] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        await checkHealth();
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    poll();
    const id = setInterval(poll, 15000);
    return () => clearInterval(id);
  }, []);

  // Suppress unused variable warning — online is used in dashboard context
  void online;
  void theme;

  return (
    <AuthContext.Provider value={auth}>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AppShell online={online}>
                  <Dashboard />
                </AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/ingest"
            element={
              <ProtectedRoute>
                <AppShell online={online}>
                  <Ingest />
                </AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/search"
            element={
              <ProtectedRoute>
                <AppShell online={online}>
                  <Search />
                </AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sectors"
            element={
              <ProtectedRoute>
                <AppShell online={online}>
                  <Sectors />
                </AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/market"
            element={
              <ProtectedRoute>
                <AppShell online={online}>
                  <MarketSummary />
                </AppShell>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

/**
 * AppShell — Wraps the existing sidebar layout for Dashboard, Ingest, etc.
 * Preserves the original sidebar navigation for non-chat pages.
 */
function AppShell({ children, online }: { children: React.ReactNode; online: boolean }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Fintex</h1>
          <div className="brand-sub">Pipeline v1.0</div>
        </div>

        <nav className="sidebar-nav">
          <a href="/chat" className="nav-link">
            <span className="nav-icon">◉</span> AI Chat
          </a>
          <a href="/dashboard" className="nav-link">
            <span className="nav-icon">◈</span> Dashboard
          </a>
          <a href="/ingest" className="nav-link">
            <span className="nav-icon">◆</span> Ingest Data
          </a>
          <a href="/search" className="nav-link">
            <span className="nav-icon">◇</span> Search
          </a>
          <a href="/sectors" className="nav-link">
            <span className="nav-icon">▣</span> Sectors
          </a>
          <a href="/market" className="nav-link">
            <span className="nav-icon">📈</span> PSX Market
          </a>
        </nav>

        <div className="sidebar-status">
          <span className={`status-dot ${online ? 'online' : 'offline'}`} />
          <span className="status-text">{online ? 'Backend Connected' : 'Disconnected'}</span>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return <AppInner />;
}
