/**
 * Authentication hook — manages Firebase auth state
 * and syncs user profile to Supabase.
 */
import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { onAuthChange, signInWithGoogle, signOut, type User } from '../lib/firebase';
import { upsertUser, type FintexUser } from '../lib/supabase';

interface AuthState {
  firebaseUser: User | null;
  fintexUser: FintexUser | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  firebaseUser: null,
  fintexUser: null,
  loading: true,
  login: async () => {},
  logout: async () => {},
});

export function useAuthProvider(): AuthState {
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [fintexUser, setFintexUser] = useState<FintexUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthChange(async (user) => {
      setFirebaseUser(user);
      if (user) {
        try {
          const profile = await upsertUser({
            uid: user.uid,
            email: user.email,
            displayName: user.displayName,
            photoURL: user.photoURL,
          });
          setFintexUser(profile);
        } catch (e) {
          console.error('Failed to sync user profile:', e);
        }
      } else {
        setFintexUser(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const login = useCallback(async () => {
    const user = await signInWithGoogle();
    const profile = await upsertUser({
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL,
    });
    setFintexUser(profile);
  }, []);

  const logout = useCallback(async () => {
    await signOut();
    setFintexUser(null);
  }, []);

  return { firebaseUser, fintexUser, loading, login, logout };
}

export { AuthContext };

export function useAuth() {
  return useContext(AuthContext);
}
