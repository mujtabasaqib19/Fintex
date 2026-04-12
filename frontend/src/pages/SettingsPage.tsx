/**
 * SettingsPage — User profile and preferences stub.
 * Will be extended with notification, API key, and appearance settings.
 */
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';
import { User, Palette, Bell, Shield, LogOut } from 'lucide-react';

export default function SettingsPage() {
  const { firebaseUser, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h2 className="settings-title">Settings</h2>
        <p className="settings-subtitle">Manage your account and preferences</p>
      </div>

      {/* Profile Section */}
      <div className="settings-section">
        <div className="settings-section-header">
          <User size={18} />
          <h3>Profile</h3>
        </div>
        <div className="settings-card">
          <div className="settings-profile-row">
            {firebaseUser?.photoURL ? (
              <img src={firebaseUser.photoURL} alt="" className="settings-avatar" />
            ) : (
              <div className="settings-avatar-placeholder">
                {(firebaseUser?.displayName || 'U').charAt(0)}
              </div>
            )}
            <div className="settings-profile-info">
              <div className="settings-profile-name">
                {firebaseUser?.displayName || 'User'}
              </div>
              <div className="settings-profile-email">
                {firebaseUser?.email || '—'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Appearance */}
      <div className="settings-section">
        <div className="settings-section-header">
          <Palette size={18} />
          <h3>Appearance</h3>
        </div>
        <div className="settings-card">
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Theme</div>
              <div className="settings-row-desc">Toggle between dark and light mode</div>
            </div>
            <button
              className="settings-theme-btn"
              onClick={toggleTheme}
            >
              {theme === 'dark' ? '🌙 Dark' : '☀️ Light'}
            </button>
          </div>
        </div>
      </div>

      {/* Notifications (stub) */}
      <div className="settings-section">
        <div className="settings-section-header">
          <Bell size={18} />
          <h3>Notifications</h3>
        </div>
        <div className="settings-card">
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Email Notifications</div>
              <div className="settings-row-desc">Coming soon</div>
            </div>
            <span className="settings-coming-soon">Coming Soon</span>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="settings-section">
        <div className="settings-section-header">
          <Shield size={18} />
          <h3>Account</h3>
        </div>
        <div className="settings-card">
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Sign Out</div>
              <div className="settings-row-desc">Log out of your Fintex account</div>
            </div>
            <button className="settings-logout-btn" onClick={logout}>
              <LogOut size={14} /> Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
