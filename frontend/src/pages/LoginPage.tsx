import { useState } from "react";
import { Dumbbell } from "lucide-react";
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
      {/* Atmósfera: un halo tenue del color de marca, sin estridencias */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, rgba(110,231,183,0.06), transparent 70%)",
        }}
      />
      <div className="animate-rise card relative w-full max-w-sm p-8">
        <div
          className="mb-6 flex h-11 w-11 items-center justify-center rounded-xl"
          style={{ background: "var(--brand-accent)" }}
        >
          <Dumbbell size={22} color="#0a0a0f" />
        </div>
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
            <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "#F77E7E18", color: "#F7A0A0" }}>
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
