import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useBrand } from "../hooks/useBrand";
import { Spinner } from "../components/ui";
import MarcaLogo from "../components/MarcaLogo";
import { api, ApiError } from "../lib/api";

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
          : "Sin conexión · reintenta",
      );
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      {/* Atmósfera de la marca. Los dos halos (azul arriba, naranja abajo)
          son la firma de DQ y estaban escritos a mano aquí: con el switch en
          el otro negocio, su coach entraba cada día por una pantalla con los
          colores del primero. Ahora los pone la PIEL. */}
      <div className="pointer-events-none fixed inset-0 login-atmosfera" />
      <div className="animate-rise card relative w-full max-w-sm p-8">
        <MarcaLogo logoUrl={brand?.logo_path ? api.mediaUrl(brand.logo_path) : null}
          skin={brand?.skin} nombre={brand?.name} alto={44} className="mb-6" />
        <h1 className="text-xl font-semibold text-zinc-100">
          {brand?.name ?? "Asesorías Fitness"}
        </h1>
        <p className="mt-1 text-sm text-zinc-500">Panel del coach</p>

        <div className="mt-7 space-y-4">
          {/* `name` + `autoComplete` + label asociada: sin ellos el gestor de
              contraseñas del móvil no ofrece rellenar (el coach entra a diario)
              y el lector de pantalla no sabe a qué campo pertenece cada
              etiqueta. */}
          <div>
            <label className="label" htmlFor="login-usuario">Usuario</label>
            <input
              id="login-usuario"
              name="username"
              type="text"
              autoComplete="username"
              className="input"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <div>
            <label className="label" htmlFor="login-password">Contraseña</label>
            <input
              id="login-password"
              name="password"
              className="input"
              type="password"
              autoComplete="current-password"
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
