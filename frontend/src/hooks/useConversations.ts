/**
 * Conversations hook — CRUD for chat conversations + search.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getConversations,
  createConversation,
  updateConversationTitle,
  deleteConversation,
  searchConversations,
  type Conversation,
} from '../lib/supabase';

export function useConversations(userId: string | undefined) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Load conversations
  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const data = await getConversations(userId);
      setConversations(data);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load();
  }, [load]);

  // Search with debounce
  const search = useCallback(
    (query: string) => {
      setSearchQuery(query);
      if (debounceRef.current) clearTimeout(debounceRef.current);

      debounceRef.current = setTimeout(async () => {
        if (!userId) return;
        if (!query.trim()) {
          load();
          return;
        }
        const data = await searchConversations(userId, query.trim());
        setConversations(data);
      }, 300);
    },
    [userId, load],
  );

  const create = useCallback(async () => {
    if (!userId) return null;
    const conv = await createConversation(userId);
    if (conv) {
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
    }
    return conv;
  }, [userId]);

  const rename = useCallback(async (id: string, title: string) => {
    await updateConversationTitle(id, title);
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c)),
    );
  }, []);

  const remove = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) setActiveConversationId(null);
    },
    [activeConversationId],
  );

  // Group conversations by date
  const grouped = groupByDate(conversations);

  return {
    conversations,
    grouped,
    activeConversationId,
    setActiveConversationId,
    searchQuery,
    search,
    create,
    rename,
    remove,
    loading,
    reload: load,
  };
}

// ── Date grouping helper ──

function groupByDate(conversations: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekStart = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: Conversation[] }[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This Week', items: [] },
    { label: 'Older', items: [] },
  ];

  for (const c of conversations) {
    const d = new Date(c.updated_at || c.created_at);
    if (d >= today) groups[0].items.push(c);
    else if (d >= yesterday) groups[1].items.push(c);
    else if (d >= weekStart) groups[2].items.push(c);
    else groups[3].items.push(c);
  }

  return groups.filter((g) => g.items.length > 0);
}
