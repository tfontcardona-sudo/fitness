import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, getToken, setToken } from "../lib/api";
import type { MeOut } from "../types";

interface AuthState {
  user: MeOut | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fuera de AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);

  // Validación inicial: si hay token, confirma que sigue vigente con /me.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch((e: any) => {
        // Solo el 401 invalida la sesión (y ese ya lo limpia la capa de API).
        // Un 502 mientras la API arranca tras un deploy, o la red caída, NO
        // pueden destruir un token válido: expulsaban al coach al login sin
        // motivo justo después de cada despliegue (auditoría 26-08).
        if (e?.status !== 401) setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // Sesión caducada (lanzado por la capa de API ante un 401).
  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await api.login(username, password);
    setToken(access_token);
    const me = await api.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
