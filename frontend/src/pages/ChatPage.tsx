/**
 * ChatPage — Overhauled chat with sidebar, conversations, accuracy badge, and optimize.
 * Preserves existing chat functionality while integrating new features.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { sendChat, generateTitle, type ChatResponse } from '../api';
import { useAuth } from '../hooks/useAuth';
import { useConversations } from '../hooks/useConversations';
import { getMessages, saveMessage } from '../lib/supabase';
import ChatSidebar from '../components/chat/Sidebar';
import AccuracyBadge from '../components/chat/AccuracyBadge';
import StockDashboard from '../components/chat/StockDashboard';
import FurtherReadingLinks from '../components/chat/FurtherReadingLinks';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  data?: ChatResponse['answer'];
  accuracyMin?: number;
  accuracyMax?: number;
  chartData?: { date: string; price: number; volume?: number }[];
  ticker?: string;
  stockSymbol?: string;  // Section 7 — for StockDashboard live data
  category?: string;
  source?: string;
}

export default function ChatPage() {
  const { fintexUser } = useAuth();
  const {
    grouped,
    activeConversationId,
    setActiveConversationId,
    searchQuery,
    search,
    create,
    rename,
  } = useConversations(fintexUser?.id);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [format, setFormat] = useState<'detailed' | 'brief' | 'bullet'>('detailed');
  const [useReasoning, setUseReasoning] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isFirstMessage = useRef(true);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  // Load conversation messages when switching
  const loadConversation = useCallback(async (convId: string) => {
    setActiveConversationId(convId);
    try {
      const msgs = await getMessages(convId);
      const converted: Message[] = [];
      for (const msg of msgs) {
        converted.push({ role: 'user', content: msg.question });
        
        // Extract metadata to restore graphs (stockSymbol) and confidence badges
        const meta = (msg.metadata as any) || {};
        const stockSymbol = meta.symbol || meta.ticker || undefined;
        
        converted.push({
          role: 'assistant',
          content: msg.answer,
          accuracyMin: msg.accuracy_min || undefined,
          accuracyMax: msg.accuracy_max || undefined,
          category: msg.category || 'general',
          source: msg.source || undefined,
          stockSymbol,
          data: {
            answer: msg.answer,
            confidence: {
              level: (msg.accuracy_min || 0) >= 80 ? 'high' : (msg.accuracy_min || 0) >= 50 ? 'medium' : 'low',
              document_count: meta.doc_count || 0
            },
            sources: meta.sources || [] 
          }
        });
      }
      setMessages(converted);
      isFirstMessage.current = converted.length === 0;
    } catch (e) {
      console.error('Failed to load messages:', e);
    }
  }, [setActiveConversationId]);

  const handleNewChat = useCallback(async () => {
    const conv = await create();
    if (conv) {
      setMessages([]);
      isFirstMessage.current = true;
    }
  }, [create]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    // If no conversation, create one
    let convId = activeConversationId;
    if (!convId) {
      const conv = await create();
      if (conv) {
        convId = conv.id;
      }
    }

    const query = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setLoading(true);

    try {
      const res = await sendChat(
        query,
        useReasoning,
        format,
        fintexUser?.id,
        convId || undefined,
      );
      const answer = res.answer?.answer || 'No answer generated.';
      
      // Use accuracy from backend pipeline (Section 6 decision matrix)
      const accuracyMin = res.accuracy_min ?? 40;
      const accuracyMax = res.accuracy_max ?? 65;

      // Use chart data from backend pipeline (Section 7.3)
      const chartData = res.chart_data || undefined;
      const ticker = res.ticker || undefined;

      // Detect stock symbol for Section 7 StockDashboard (Always show if ticker found)
      const stockSymbol = res.ticker || ticker;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: answer,
          data: res.answer,
          accuracyMin,
          accuracyMax,
          chartData,
          ticker,
          stockSymbol,
          category: res.category || 'general',
          source: res.source,
        },
      ]);

      // Save to Supabase
      if (convId && fintexUser) {
        await saveMessage({
          conversation_id: convId,
          user_id: fintexUser.id,
          question: query,
          answer,
          category: res.category || 'general',
          accuracy_min: accuracyMin,
          accuracy_max: accuracyMax,
          source: res.source || (res.reasoning_used ? 'reasoning' : 'simple'),
          metadata: res.metadata,
        });

        // Auto-name conversation on first message (Section 4.2)
        if (isFirstMessage.current) {
          try {
            const titleRes = await generateTitle(query);
            await rename(convId, titleRes.title);
          } catch {
            // Fallback: use first 60 chars
            await rename(convId, query.slice(0, 60));
          }
          isFirstMessage.current = false;
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Something went wrong';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `⚠ Error: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getSourceIcon = (source: { type?: string; source_type?: string }) => {
    if (source.source_type === 'Live Web Search') return '🌐';
    if (source.type === 'stock_market') return '📈';
    if (source.type === 'document') return '📄';
    return '📊';
  };

  const getSourceLabel = (source: { type?: string; title?: string; symbol?: string; series_id?: string; provider?: string }) => {
    if (source.title) return source.title;
    if (source.symbol) return source.symbol;
    if (source.series_id) return `${source.series_id} [${source.provider || ''}]`;
    return 'Unknown';
  };

  return (
    <div className="chat-page-layout">
      <ChatSidebar
        conversations={grouped}
        activeConversationId={activeConversationId}
        searchQuery={searchQuery}
        onSearch={search}
        onNewChat={handleNewChat}
        onSelectConversation={loadConversation}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className={`chat-main ${sidebarCollapsed ? 'chat-main--expanded' : ''}`}>
        {/* Controls */}
        <div className="chat-controls">
          <div className="format-switcher">
            {(['detailed', 'brief', 'bullet'] as const).map((f) => (
              <button
                key={f}
                className={`format-option ${format === f ? 'active' : ''}`}
                onClick={() => setFormat(f)}
              >
                {f}
              </button>
            ))}
          </div>
          <label className="reasoning-toggle">
            <input
              type="checkbox"
              checked={useReasoning}
              onChange={(e) => setUseReasoning(e.target.checked)}
            />
            <span>Tree of Thought</span>
          </label>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">
                <span className="fx-mono" style={{ fontSize: '2rem' }}>FX</span>
              </div>
              <h3>Start a Conversation</h3>
              <p>Ask about Pakistan's economy, stock market, banking sector, or financial data</p>
              <div className="chat-suggestions">
                {[
                  'What is the current USD/PKR rate?',
                  'Explain the latest SBP policy decision',
                  'How are cement exports performing?',
                  'PSX market overview',
                ].map((q) => (
                  <button
                    key={q}
                    className="btn btn-sm chat-suggestion"
                    onClick={() => setInput(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              <div className="message-bubble">
                {msg.role === 'assistant' ? (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                ) : (
                  <p>{msg.content}</p>
                )}

                {/* Section 7 — Stock Dashboards (Renders whenever a ticker is detected) */}
                {msg.role === 'assistant' && msg.stockSymbol && (
                  <div className="stock-dash-grid">
                    {msg.stockSymbol.split(',').map(sym => (
                       <StockDashboard key={sym} ticker={sym.trim()} />
                    ))}
                  </div>
                )}

                {/* Further Reading Links for theory answers */}
                {msg.role === 'assistant' && msg.content && (
                  <FurtherReadingLinks content={msg.content} />
                )}

                {/* Accuracy Badge */}
                {msg.role === 'assistant' && msg.accuracyMin && msg.accuracyMax && (
                  <div className="message-footer">
                    <AccuracyBadge min={msg.accuracyMin} max={msg.accuracyMax} sourceLabel={msg.source} />
                  </div>
                )}

                {/* Confidence badge (existing) */}
                {msg.data?.confidence && (
                  <div className={`confidence-badge ${msg.data.confidence.level}`}>
                    {msg.data.confidence.level === 'high' ? '●' : msg.data.confidence.level === 'medium' ? '◐' : '○'}
                    {msg.data.confidence.document_count ? `${msg.data.confidence.document_count} docs` : ''}
                    {msg.data.confidence.timeseries_count ? ` · ${msg.data.confidence.timeseries_count} series` : ''}
                  </div>
                )}

                {/* Sources */}
                {msg.data?.sources && msg.data.sources.length > 0 && (
                  <div className="chat-sources">
                    <div className="chat-sources-title">Sources ({msg.data.sources.length})</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {msg.data.sources.slice(0, 7).map((src, j) => (
                        <span key={j} className="source-tag">
                          {getSourceIcon(src)} {getSourceLabel(src).slice(0, 40)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <div className="message-bubble">
                <div className="thinking-dots">
                  <span /><span /><span />
                </div>
                <span className="thinking-text">
                  {useReasoning ? 'Reasoning with Tree of Thought...' : 'Retrieving and synthesizing...'}
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <input
              type="text"
              placeholder="Ask about Pakistan's economy, markets, or financial data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
              disabled={loading}
            />
          </div>
          <button className="btn btn-primary" onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? <span className="spinner" /> : '→'}
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
