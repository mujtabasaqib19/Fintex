/**
 * Chat Sidebar — Full-featured sidebar with search, history, and user profile.
 */
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  MessageSquare,
  BarChart3,
  Settings,
  Plus,
  Search,
  X,
  LogOut,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react';
import ThemeToggle from '../shared/ThemeToggle';
import { useAuth } from '../../hooks/useAuth';
import type { Conversation } from '../../lib/supabase';

interface Props {
  conversations: { label: string; items: Conversation[] }[];
  activeConversationId: string | null;
  searchQuery: string;
  onSearch: (q: string) => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function ChatSidebar({
  conversations,
  activeConversationId,
  searchQuery,
  onSearch,
  onNewChat,
  onSelectConversation,
  collapsed,
  onToggleCollapse,
}: Props) {
  const { firebaseUser, logout } = useAuth();
  const [hoveredConv, setHoveredConv] = useState<string | null>(null);

  if (collapsed) {
    return (
      <aside className="chat-sidebar chat-sidebar--collapsed">
        <button className="sidebar-collapse-btn" onClick={onToggleCollapse} title="Expand sidebar">
          <PanelLeft size={20} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="chat-sidebar">
      {/* Header */}
      <div className="chat-sidebar-header">
        <div className="chat-sidebar-brand">
          <span className="fx-mono">FX</span>
          <span className="chat-sidebar-wordmark">Fintex</span>
        </div>
        <button className="sidebar-collapse-btn" onClick={onToggleCollapse} title="Collapse sidebar">
          <PanelLeftClose size={20} />
        </button>
      </div>

      {/* New Chat */}
      <button className="new-chat-btn" onClick={onNewChat}>
        <Plus size={16} /> New Chat
      </button>

      {/* Search */}
      <div className="sidebar-search">
        <Search size={14} className="sidebar-search-icon" />
        <input
          type="text"
          placeholder="Search chats..."
          value={searchQuery}
          onChange={(e) => onSearch(e.target.value)}
          className="sidebar-search-input"
        />
        {searchQuery && (
          <button className="sidebar-search-clear" onClick={() => onSearch('')}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Nav Links */}
      <div className="sidebar-nav-links">
        <NavLink to="/chat" end className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <MessageSquare size={16} /> Chats
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <BarChart3 size={16} /> Dashboard
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <Settings size={16} /> Settings
        </NavLink>
      </div>

      {/* Chat History */}
      <div className="sidebar-history">
        {conversations.map((group) => (
          <div key={group.label} className="history-group">
            <div className="history-group-label">{group.label}</div>
            {group.items.map((conv) => (
              <button
                key={conv.id}
                className={`history-item ${conv.id === activeConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
                onMouseEnter={() => setHoveredConv(conv.id)}
                onMouseLeave={() => setHoveredConv(null)}
                title={conv.title || 'Untitled'}
              >
                <MessageSquare size={14} />
                <span className="history-item-title">
                  {(conv.title || 'New Chat').slice(0, 30)}
                </span>
                {hoveredConv === conv.id && (
                  <span className="history-item-time">
                    {new Date(conv.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                )}
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* User Profile */}
      <div className="sidebar-user">
        <ThemeToggle className="sidebar-theme-toggle" />
        <div className="sidebar-user-info">
          {firebaseUser?.photoURL ? (
            <img src={firebaseUser.photoURL} alt="" className="sidebar-avatar" />
          ) : (
            <div className="sidebar-avatar-placeholder">
              {(firebaseUser?.displayName || 'U').charAt(0)}
            </div>
          )}
          <div className="sidebar-user-text">
            <div className="sidebar-user-name">{firebaseUser?.displayName || 'User'}</div>
            <div className="sidebar-user-email">{(firebaseUser?.email || '').slice(0, 24)}</div>
          </div>
        </div>
        <button className="sidebar-signout" onClick={logout} title="Sign out">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
