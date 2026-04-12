/**
 * Supabase client for the Fintex frontend.
 * Handles user profiles, conversations, and chat history.
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://rezibbwmvvojbjoftpbm.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'fake-anon-key-for-dev';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// ── User Operations ──

export interface FintexUser {
  id: string;
  firebase_uid: string;
  email: string;
  display_name: string | null;
  photo_url: string | null;
  created_at: string;
  last_login: string;
}

export async function upsertUser(firebaseUser: {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
}): Promise<FintexUser | null> {
  // Check if user exists
  const { data: existing } = await supabase
    .from('users')
    .select('*')
    .eq('firebase_uid', firebaseUser.uid)
    .single();

  if (existing) {
    // Update last_login
    const { data } = await supabase
      .from('users')
      .update({ last_login: new Date().toISOString() })
      .eq('firebase_uid', firebaseUser.uid)
      .select()
      .single();
    return data;
  }

  // New user
  const { data } = await supabase
    .from('users')
    .insert({
      firebase_uid: firebaseUser.uid,
      email: firebaseUser.email || '',
      display_name: firebaseUser.displayName,
      photo_url: firebaseUser.photoURL,
    })
    .select()
    .single();
  return data;
}

// ── Conversation Operations ──

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export async function getConversations(userId: string): Promise<Conversation[]> {
  const { data } = await supabase
    .from('conversations')
    .select('*')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false });
  return data || [];
}

export async function createConversation(userId: string, title?: string): Promise<Conversation | null> {
  const { data } = await supabase
    .from('conversations')
    .insert({ user_id: userId, title: title || 'New Chat' })
    .select()
    .single();
  return data;
}

export async function updateConversationTitle(conversationId: string, title: string) {
  await supabase
    .from('conversations')
    .update({ title, updated_at: new Date().toISOString() })
    .eq('id', conversationId);
}

export async function deleteConversation(conversationId: string) {
  await supabase
    .from('conversations')
    .delete()
    .eq('id', conversationId);
}

export async function searchConversations(userId: string, query: string): Promise<Conversation[]> {
  const { data } = await supabase
    .from('conversations')
    .select('*')
    .eq('user_id', userId)
    .ilike('title', `%${query}%`)
    .order('updated_at', { ascending: false });
  return data || [];
}

// ── Message Operations ──

export interface ChatMessage {
  id: string;
  conversation_id: string;
  user_id: string;
  question: string;
  answer: string;
  category: string;
  subcategory: string | null;
  accuracy_min: number | null;
  accuracy_max: number | null;
  source: string | null;
  date: string;
  metadata: Record<string, unknown> | null;
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  const { data } = await supabase
    .from('messages')
    .select('*')
    .eq('conversation_id', conversationId)
    .order('date', { ascending: true });
  return data || [];
}

export async function saveMessage(msg: {
  conversation_id: string;
  user_id: string;
  question: string;
  answer: string;
  category: string;
  subcategory?: string;
  accuracy_min?: number;
  accuracy_max?: number;
  source?: string;
  metadata?: Record<string, unknown>;
}): Promise<ChatMessage | null> {
  const { data } = await supabase
    .from('messages')
    .insert(msg)
    .select()
    .single();
  return data;
}
