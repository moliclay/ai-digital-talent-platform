import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, tokenStore, type Me } from "./api";

type AuthContextValue = {
  me: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((value) => {
        if (alive) setMe(value);
      })
      .catch(() => {
        tokenStore.clear();
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    tokenStore.set(result.token);
    const current = await api.me();
    setMe(current);
    return current;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // 令牌已失效也要清本地
    } finally {
      tokenStore.clear();
      setMe(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ me, loading, login, logout }),
    [me, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return value;
}
