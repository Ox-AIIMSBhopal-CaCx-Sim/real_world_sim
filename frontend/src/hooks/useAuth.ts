import { useCallback, useState } from 'react';
import { loginUser, registerUser } from '../api/client';

const SESSION_KEY = 'des-sim-username';

function loadSession(): string | null {
  try {
    return localStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

export function useAuth() {
  const [username, setUsername] = useState<string | null>(() => loadSession());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const persist = useCallback((name: string | null) => {
    if (name) {
      localStorage.setItem(SESSION_KEY, name);
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
    setUsername(name);
  }, []);

  const login = useCallback(
    async (name: string, password: string) => {
      setBusy(true);
      setError(null);
      try {
        const res = await loginUser({ username: name.trim(), password });
        persist(res.username);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [persist],
  );

  const register = useCallback(
    async (name: string, password: string) => {
      setBusy(true);
      setError(null);
      try {
        const res = await registerUser({ username: name.trim(), password });
        persist(res.username);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [persist],
  );

  const logout = useCallback(() => {
    persist(null);
    setError(null);
  }, [persist]);

  return { username, login, register, logout, error, setError, busy };
}
