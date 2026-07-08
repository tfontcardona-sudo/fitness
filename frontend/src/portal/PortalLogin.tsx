import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { portalLogin, portalSession, PortalError } from "./portalApi";

/**
 * Login del portal del cliente (ruta /portal). Entra con su email y la
 * contraseña que recibió por correo. "Recordarme" guarda la sesión para
 * autorrellenar y entrar directo la próxima vez. El enlace por token
 * (/p/:token) sigue funcionando en paralelo.
 */
export default function PortalLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Si ya hay sesión recordada, entra directo. Si no, autorrellena el email.
  useEffect(() => {
    const t = portalSession.token();
    if (t) {
      nav(`/p/${t}`, { replace: true });
      return;
    }
    const savedEmail = portalSession.email();
    if (savedEmail) setEmail(savedEmail);
  }, [nav]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const { token } = await portalLogin(email.trim(), password);
      if (remember) portalSession.save(token, email.trim());
      else portalSession.clear();
      nav(`/p/${token}`, { replace: true });
    } catch (err) {
      setError(err instanceof PortalError ? err.message : "No se pudo entrar. Inténtalo de nuevo.");
      setBusy(false);
    }
  }

  return (
    <div className="portal-root mx-auto flex min-h-screen max-w-md flex-col justify-center px-6"
      style={{ paddingBottom: "10vh" }}>
      <div className="mb-6 flex flex-col items-center text-center">
        <img src="/dq-logo.png" alt="" className="mb-3 h-12 w-auto rounded-xl shadow-sm" />
        <h1 className="text-2xl font-semibold">Entra a tu portal</h1>
        <p className="mt-1 text-sm opacity-60">Usa el email y la contraseña que te enviamos por correo.</p>
      </div>

      <form onSubmit={submit} className="portal-card space-y-4 p-5">
        <label className="block">
          <span className="mb-1 block text-xs font-medium opacity-70">Email</span>
          <input
            type="email" inputMode="email" autoComplete="username" required
            value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@email.com"
            className="w-full rounded-xl px-3 py-3 text-base outline-none"
            style={{ border: "1px solid var(--p-line)", background: "var(--p-card-top)", color: "var(--p-ink)" }}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium opacity-70">Contraseña</span>
          <input
            type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-xl px-3 py-3 text-base outline-none"
            style={{ border: "1px solid var(--p-line)", background: "var(--p-card-top)", color: "var(--p-ink)" }}
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)}
            className="h-4 w-4" style={{ accentColor: "var(--p-accent)" }} />
          <span className="opacity-80">Recordarme en este dispositivo</span>
        </label>

        {error && (
          <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "rgba(179,38,30,0.10)", color: "#b3261e" }}>
            {error}
          </p>
        )}

        <button
          type="submit" disabled={busy}
          className="portal-btn3d flex w-full items-center justify-center gap-2 py-3 text-sm font-semibold"
          style={{ background: "var(--p-accent)", color: "#fff" }}
        >
          <LogIn size={16} /> {busy ? "Entrando…" : "Entrar"}
        </button>
      </form>

      <p className="mt-5 text-center text-xs opacity-50">
        ¿No tienes tus datos? Pídeselos a tu coach y te reenviará el acceso.
      </p>
    </div>
  );
}
