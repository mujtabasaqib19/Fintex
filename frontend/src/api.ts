const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Health ──
export const checkHealth = () => request<{ status: string; timestamp: string }>('/health');

// ── Chat ──
export interface ChatResponse {
  query: string;
  answer: {
    answer: string;
    confidence: { level: string; document_count?: number; timeseries_count?: number; stock_market_count?: number };
    sources: Array<{
      type: string;
      title?: string;
      url?: string;
      source_type?: string;
      series_id?: string;
      symbol?: string;
      provider?: string;
    }>;
  };
  reasoning_used: boolean;
  category?: string;
  subcategory?: string;
  accuracy_min?: number;
  accuracy_max?: number;
  source?: string;
  chart_data?: Array<{ date: string; price: number; volume?: number }>;
  ticker?: string;
  metadata?: Record<string, any>;
}

export const sendChat = (
  query: string,
  useReasoning = true,
  format = 'detailed',
  userId?: string,
  conversationId?: string,
) =>
  request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      query,
      use_reasoning: useReasoning,
      format,
      user_id: userId,
      conversation_id: conversationId,
    }),
  });

export const generateTitle = (query: string) =>
  request<{ title: string }>('/chat/title', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });

// ── Dashboard ──
export interface SectorInfo {
  sector: string;
  document_count: number;
  series_count: number;
}

export const getSectors = () => request<{ sectors: SectorInfo[] }>('/dashboard/sectors');

export interface RecentDoc {
  id: string;
  source_type: string;
  sector_category: string;
  title: string;
  ingested_at: string;
}

export const getRecentActivity = (limit = 20) =>
  request<{ recent_documents: RecentDoc[] }>(`/dashboard/recent?limit=${limit}`);

// ── Search ──
export interface SearchResult {
  id: string;
  title: string;
  content: string;
  source_type: string;
  sector_category: string;
  url?: string;
  similarity: number;
  published_at?: string;
}

export const searchDocuments = (query: string, limit = 10, sectorCategory?: string, sourceType?: string) =>
  request<{ query: string; count: number; results: SearchResult[] }>('/search/documents', {
    method: 'POST',
    body: JSON.stringify({
      query,
      limit,
      sector_category: sectorCategory || undefined,
      source_type: sourceType || undefined,
    }),
  });

// ── Ingest ──
export const ingestUrl = (url: string, sourceType?: string, sectorCategory?: string) =>
  request<{ status: string; documents_created: number }>('/ingest/url', {
    method: 'POST',
    body: JSON.stringify({ url, source_type: sourceType || undefined, sector_category: sectorCategory || undefined }),
  });

export const ingestText = (title: string, content: string, sourceType: string, sectorCategory?: string) =>
  request<{ status: string; documents_created: number }>('/ingest/text', {
    method: 'POST',
    body: JSON.stringify({ title, content, source_type: sourceType, sector_category: sectorCategory || undefined }),
  });

// ── Sector detail ──
export const getSectorSummary = (sector: string, limit = 10) =>
  request<{ sector: string; series_count: number; data: unknown[] }>(`/sector/${sector}/summary?limit=${limit}`);

// ── PSX Market Summary ──
export interface PSXHistoryPoint {
  date: string;
  index: number;
  volume: number;
  change: number;
}

export interface PSXMarketActivity {
  source: string;
  current_index: number;
  change: number;
  percent_change: number;
  high: number;
  low: number;
  volume: number;
  previous_close?: number;
  history: PSXHistoryPoint[];
}

export interface PSXBoardScrip {
  symbol: string;
  ldcp: number;
  open: number;
  high: number;
  low: number;
  current: number;
  change: number;
  volume: number;
  bull: boolean;
}

export interface PSXSectorGroup {
  sector: string;
  scrips: PSXBoardScrip[];
}

export interface PSXMarketActivity {
  source: string;
  current_index: number;
  change: number;
  percent_change: number;
  high: number;
  low: number;
  volume: number;
  previous_close?: number;
  history: PSXHistoryPoint[];
}

export interface PSXAnnouncement {
  type: string;
  message: string;
  timestamp: string;
  symbol?: string;
}

export interface PSXAnnouncements {
  exchange_announcements: PSXAnnouncement[];
  company_announcements: PSXAnnouncement[];
}

export const getPSXMarketActivity = () =>
  request<PSXMarketActivity>('/psx/market-activity');

export const getPSXFullBoard = () =>
  request<{ sectors: PSXSectorGroup[] }>('/psx/full-board');

export const getPSXAnnouncements = () =>
  request<PSXAnnouncements>('/psx/announcements');

// ── Section 7: Stock Query (real Supabase stock_prices data) ──

export interface StockDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  daily_change_pct: number | null;
}

export interface StockStats {
  period_high: number;
  period_low: number;
  avg_close: number;
  total_volume: number;
  start_price: number;
  end_price: number;
  change_pct: number;
}

export interface StockAvailability {
  earliest_date: string;
  latest_date: string;
  total_records: number;
}

export interface StockQueryResponse {
  symbol: string;
  start_date: string;
  end_date: string;
  data: StockDataPoint[];
  stats: StockStats | null;
  availability: StockAvailability | null;
  has_zero_rows: boolean;
  support_level: number | null;
  resistance_level: number | null;
  not_found?: boolean;
}

export const fetchStockQuery = (
  symbol: string,
  startDate: string,
  endDate: string,
) =>
  request<StockQueryResponse>(
    `/stock/query?symbol=${encodeURIComponent(symbol)}&start_date=${startDate}&end_date=${endDate}`,
  );

// ── NEW: Fundamentals & Alerts ──

export interface StockFundamental {
  fiscal_year: number;
  revenue: number;
  net_profit: number;
  eps: number;
  pe_ratio: number;
  dividend_yield: number;
  market_cap: number;
}

export const fetchStockFundamentals = (symbol: string) =>
  request<{ symbol: string; data: StockFundamental[] }>(`/stock/fundamentals?symbol=${encodeURIComponent(symbol)}`);

export const createStockAlert = (symbol: string, price: number, condition: 'above' | 'below', userId: string) =>
  request<any>(`/stock/alert?symbol=${symbol}&price=${price}&condition=${condition}&user_id=${userId}`, {
    method: 'POST',
  });

export const fetchStockAlerts = (userId: string) =>
  request<any[]>(`/stock/alerts?user_id=${userId}`);

