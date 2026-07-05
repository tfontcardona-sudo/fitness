import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { Spinner } from "../components/ui";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const { brand } = useBrand();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!username || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch (e) {
      // El error no se disculpa y es concreto (skill): credenciales o caída.
      setError(
        e instanceof ApiError && e.status === 401
          ? "Usuario o contraseña incorrectos."
          : "No se pudo conectar. Inténtalo de nuevo.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      {/* Atmósfera: azul arriba, naranja abajo — la firma visual DQ */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(46,94,140,0.10), transparent 70%)," +
            "radial-gradient(50% 40% at 50% 100%, rgba(232,131,58,0.07), transparent 70%)",
        }}
      />
      <div className="animate-rise card relative w-full max-w-sm p-8">
        <img src="/dq-logo.png" alt="DQ" className="mb-6 h-11 w-auto rounded-lg" />
        <h1 className="text-xl font-semibold text-zinc-100">
          {brand?.name ?? "Asesorías Fitness"}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">Panel del coach</p>

        <div className="mt-7 space-y-4">
          <div>
            <label className="label">Usuario</label>
            <input
              className="input"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>

          {error && (
            <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "rgba(194,69,58,0.10)", color: "#B4453A" }}>
              {error}
            </p>
          )}

          <button className="btn btn-primary w-full" disabled={busy} onClick={submit}>
            {busy ? <Spinner /> : "Entrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
