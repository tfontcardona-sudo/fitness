import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, Loader2 } from "lucide-react";

/**
 * CUESTIONARIO INICIAL de Professional (/anamnesis/{token}) — público, llega
 * por email al contratar.
 *
 * Es corto a propósito: cinco minutos y solo lo que hace falta para preparar
 * el plan. Cuatro bloques (tú · tu objetivo · tu salud · tu día a día), y lo
 * que no aplica al servicio contratado ni se pregunta: a un cliente de DIETA
 * no se le piden días de entreno ni material; a uno de ENTRENAMIENTO no se le
 * pregunta por comidas ni alergias.
 *
 * Al enviarlo, el cliente queda registrado con su ficha y su coach lo ve en el
 * panel listo para asignarle su planificación.
 */

interface EstadoPublico {
  first_name: string;
  package_tier: "nutri" | "train" | "full";
  anamnesis_done: boolean;
  brand_name: string;
}

const OBJETIVOS = [
  { v: "muscle_gain", label: "Ganar masa muscular" },
  { v: "fat_loss", label: "Perder grasa / definir" },
  { v: "maintenance", label: "Mantenerme y estar en forma" },
] as const;

const NIVELES = [
  { v: "beginner", label: "Empiezo ahora" },
  { v: "intermediate", label: "Llevo tiempo entrenando" },
  { v: "advanced", label: "Tengo mucha experiencia" },
] as const;

const ACTIVIDAD = [
  { v: "sedentary", label: "Sentado casi todo el día" },
  { v: "light", label: "De pie a ratos" },
  { v: "active", label: "Trabajo físico" },
  { v: "very_active", label: "Trabajo físico intenso" },
] as const;

const PATRONES = [
  { v: "", label: "Como de todo" },
  { v: "vegetariano", label: "Vegetariano" },
  { v: "vegano", label: "Vegano" },
  { v: "pescetariano", label: "Pescetariano" },
  { v: "sin_cerdo", label: "Sin cerdo" },
  { v: "halal", label: "Halal" },
  { v: "kosher", label: "Kosher" },
] as const;

export default function AnamnesisPage() {
  const { token } = useParams();
  const [estado, setEstado] = useState<EstadoPublico | null>(null);
  const [tokenBad, setTokenBad] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [hecho, setHecho] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Campos
  const [sex, setSex] = useState("");
  const [birth, setBirth] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [goal, setGoal] = useState("");
  const [goalWeight, setGoalWeight] = useState("");
  const [level, setLevel] = useState("beginner");
  const [injuries, setInjuries] = useState("");
  const [medical, setMedical] = useState("");
  const [days, setDays] = useState("3");
  const [place, setPlace] = useState("gym");
  const [minutes, setMinutes] = useState("60");
  const [activity, setActivity] = useState("light");
  const [meals, setMeals] = useState("4");
  const [allergies, setAllergies] = useState("");
  const [dislikes, setDislikes] = useState("");
  const [pattern, setPattern] = useState("");
  const [notes, setNotes] = useState("");
  const [consent, setConsent] = useState(false);

  useEffect(() => {
    fetch(`/api/p/${token}`)
      .then(async (r) => {
        if (r.status === 404) { setTokenBad(true); return; }
        const d = await r.json();
        setEstado(d);
        if (d.anamnesis_done) setHecho(true);
      })
      .catch(() => { /* fallo de red: el backend re-valida al enviar */ });
  }, [token]);

  const tier = estado?.package_tier ?? "full";
  const conDieta = tier === "nutri" || tier === "full";
  const conEntreno = tier === "train" || tier === "full";

  const lista = (s: string) =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  const valido =
    sex !== "" && birth !== "" && Number(height) > 80 && Number(weight) > 30 &&
    goal !== "" && consent;

  async function enviar() {
    if (!valido || enviando) return;
    setEnviando(true);
    setError(null);
    const body: Record<string, unknown> = {
      sex, birth_date: birth,
      height_cm: Number(height), start_weight_kg: Number(weight),
      goal_type: goal,
      goal_weight_kg: goalWeight ? Number(goalWeight) : null,
      level,
      injuries_notes: injuries || null,
      medical_notes: medical || null,
      daily_activity_level: activity,
      lifestyle_notes: notes || null,
      consent_accepted: true,
    };
    if (conEntreno) {
      body.training_days = Number(days);
      body.training_place = place;
      body.session_max_min = Number(minutes);
    }
    if (conDieta) {
      body.meals_per_day = Number(meals);
      body.food_allergies = lista(allergies);
      body.food_dislikes = lista(dislikes);
      if (pattern) body.diet_pattern = pattern;
    }
    try {
      const r = await fetch(`/api/p/${token}/anamnesis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        let msg = "No se pudo enviar. Revisa los datos e inténtalo de nuevo.";
        try {
          const d = await r.json();
          if (typeof d?.detail === "string") msg = d.detail;
        } catch { /* sin cuerpo JSON */ }
        throw new Error(msg);
      }
      setHecho(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e: any) {
      setError(e?.message ?? "No se pudo enviar. Inténtalo de nuevo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0F0E0C", color: "#F5F3EE" }}>
      <div className="mx-auto max-w-2xl px-5 py-10">
        <header className="mb-8 flex flex-col items-center text-center">
          <img src="/brand-logo.png" alt="" className="h-14 w-auto rounded-xl shadow-sm" />
          <h1 className="mt-4 text-2xl font-bold">Tu cuestionario inicial</h1>
          <p className="mt-1 max-w-md text-sm opacity-70">
            {estado ? `Hola ${estado.first_name}. ` : ""}
            Cinco minutos y preparamos tu plan a medida. Solo te preguntamos lo
            que necesitamos de verdad.
          </p>
        </header>

        {tokenBad ? (
          <Card>
            <h2 className="text-lg font-bold">Este enlace no es válido</h2>
            <p className="mt-2 text-sm opacity-75">
              Puede que esté incompleto o haya caducado. Escríbenos y te
              enviamos uno nuevo al momento.
            </p>
          </Card>
        ) : hecho ? (
          <Card>
            <CheckCircle2 size={40} className="mx-auto" style={{ color: "#B58910" }} />
            <h2 className="mt-3 text-center text-lg font-bold">¡Cuestionario recibido!</h2>
            <p className="mt-2 text-center text-sm opacity-75">
              Ya tenemos tus datos. Preparamos tu plan y te lo enviamos por
              correo. Revisa también la carpeta de spam.
            </p>
          </Card>
        ) : (
          <div className="space-y-4">
            <Bloque n={1} titulo="Tú">
              <Fila>
                <Campo label="Sexo">
                  <select className="inp" value={sex} onChange={(e) => setSex(e.target.value)}>
                    <option value="">Elige…</option>
                    <option value="female">Mujer</option>
                    <option value="male">Hombre</option>
                  </select>
                </Campo>
                <Campo label="Fecha de nacimiento">
                  <input className="inp" type="date" value={birth} onChange={(e) => setBirth(e.target.value)} />
                </Campo>
              </Fila>
              <Fila>
                <Campo label="Altura (cm)">
                  <input className="inp" type="number" inputMode="numeric" value={height}
                    onChange={(e) => setHeight(e.target.value)} placeholder="170" />
                </Campo>
                <Campo label="Peso actual (kg)">
                  <input className="inp" type="number" inputMode="decimal" step="0.1" value={weight}
                    onChange={(e) => setWeight(e.target.value)} placeholder="72,5" />
                </Campo>
              </Fila>
            </Bloque>

            <Bloque n={2} titulo="Tu objetivo">
              <Campo label="¿Qué quieres conseguir?">
                <div className="grid gap-2 sm:grid-cols-3">
                  {OBJETIVOS.map((o) => (
                    <button key={o.v} type="button" onClick={() => setGoal(o.v)}
                      className="rounded-xl border px-3 py-3 text-sm font-medium transition-colors"
                      style={goal === o.v
                        ? { borderColor: "#E9A90F", background: "rgba(233,169,15,0.12)", color: "#F7C33A" }
                        : { borderColor: "rgba(245,243,238,0.16)", color: "#DAD5C9" }}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </Campo>
              <Fila>
                <Campo label="Peso al que te gustaría llegar (opcional)">
                  <input className="inp" type="number" inputMode="decimal" step="0.1" value={goalWeight}
                    onChange={(e) => setGoalWeight(e.target.value)} placeholder="—" />
                </Campo>
                <Campo label="Tu experiencia">
                  <select className="inp" value={level} onChange={(e) => setLevel(e.target.value)}>
                    {NIVELES.map((n) => <option key={n.v} value={n.v}>{n.label}</option>)}
                  </select>
                </Campo>
              </Fila>
            </Bloque>

            <Bloque n={3} titulo="Tu salud">
              <Campo label="Lesiones o molestias (rodilla, hombro, espalda…)">
                <textarea className="inp" rows={2} value={injuries} onChange={(e) => setInjuries(e.target.value)}
                  placeholder="Si no tienes ninguna, déjalo en blanco" />
              </Campo>
              <Campo label="Enfermedades, tratamientos o medicación">
                <textarea className="inp" rows={2} value={medical} onChange={(e) => setMedical(e.target.value)}
                  placeholder="Tensión, diabetes, tiroides… y lo que tomes" />
              </Campo>
            </Bloque>

            <Bloque n={4} titulo="Tu día a día">
              <Campo label="¿Cómo es tu actividad fuera del entreno?">
                <select className="inp" value={activity} onChange={(e) => setActivity(e.target.value)}>
                  {ACTIVIDAD.map((a) => <option key={a.v} value={a.v}>{a.label}</option>)}
                </select>
              </Campo>

              {conEntreno && (
                <Fila>
                  <Campo label="Días que puedes entrenar">
                    <select className="inp" value={days} onChange={(e) => setDays(e.target.value)}>
                      {[2, 3, 4, 5, 6].map((d) => <option key={d} value={d}>{d} días</option>)}
                    </select>
                  </Campo>
                  <Campo label="¿Dónde entrenas?">
                    <select className="inp" value={place} onChange={(e) => setPlace(e.target.value)}>
                      <option value="gym">En el gimnasio</option>
                      <option value="home">En casa</option>
                    </select>
                  </Campo>
                  <Campo label="Minutos por sesión">
                    <select className="inp" value={minutes} onChange={(e) => setMinutes(e.target.value)}>
                      {[30, 45, 60, 75, 90].map((m) => <option key={m} value={m}>{m} min</option>)}
                    </select>
                  </Campo>
                </Fila>
              )}

              {conDieta && (
                <>
                  <Fila>
                    <Campo label="Comidas al día">
                      <select className="inp" value={meals} onChange={(e) => setMeals(e.target.value)}>
                        {[3, 4, 5].map((m) => <option key={m} value={m}>{m} comidas</option>)}
                      </select>
                    </Campo>
                    <Campo label="¿Sigues alguna pauta?">
                      <select className="inp" value={pattern} onChange={(e) => setPattern(e.target.value)}>
                        {PATRONES.map((p) => <option key={p.v} value={p.v}>{p.label}</option>)}
                      </select>
                    </Campo>
                  </Fila>
                  <Campo label="Alergias o intolerancias (separadas por comas)">
                    <input className="inp" value={allergies} onChange={(e) => setAllergies(e.target.value)}
                      placeholder="lactosa, frutos secos…" />
                  </Campo>
                  <Campo label="Alimentos que NO quieres (separados por comas)">
                    <input className="inp" value={dislikes} onChange={(e) => setDislikes(e.target.value)}
                      placeholder="pescado, brócoli…" />
                  </Campo>
                </>
              )}

              <Campo label="Algo más que debamos saber (opcional)">
                <textarea className="inp" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)}
                  placeholder="Horarios, turnos, cómo duermes, tu nivel de estrés…" />
              </Campo>
            </Bloque>

            <div className="rounded-2xl border p-5" style={{ borderColor: "rgba(245,243,238,0.14)" }}>
              <label className="flex cursor-pointer items-start gap-3 text-sm">
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 h-4 w-4" style={{ accentColor: "#E9A90F" }} />
                <span className="opacity-80">
                  Autorizo el tratamiento de mis datos (incluidos los de salud)
                  para preparar y hacer el seguimiento de mi plan. Puedo pedir su
                  eliminación cuando quiera.
                </span>
              </label>

              {error && (
                <p className="mt-3 rounded-xl px-3 py-2 text-sm"
                  style={{ background: "rgba(240,113,106,0.14)", color: "#F0716A" }}>
                  {error}
                </p>
              )}

              <button onClick={enviar} disabled={!valido || enviando}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3.5 text-sm font-bold transition-transform active:scale-[0.98] disabled:opacity-50"
                style={{ background: "#E9A90F", color: "#241C04" }}>
                {enviando ? <><Loader2 size={16} className="animate-spin" /> Enviando…</> : "Enviar mi cuestionario"}
              </button>
              {!valido && (
                <p className="mt-2 text-center text-xs opacity-50">
                  Completa sexo, fecha de nacimiento, altura, peso, objetivo y la autorización.
                </p>
              )}
            </div>

            <p className="pb-6 text-center text-xs opacity-50">
              Tus datos se usan solo para preparar y seguir tu plan.
            </p>
          </div>
        )}
      </div>

      <style>{`
        .inp {
          width: 100%; border-radius: 12px; padding: 12px 14px; font-size: 16px;
          background: #1C1913; color: #F5F3EE;
          border: 1px solid rgba(245,243,238,0.16); outline: none;
        }
        .inp:focus { border-color: #E9A90F; box-shadow: 0 0 0 3px rgba(233,169,15,0.14); }
        .inp::placeholder { color: #8A8274; }
      `}</style>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border p-6" style={{ borderColor: "rgba(245,243,238,0.16)", background: "#17150F" }}>
      {children}
    </div>
  );
}

function Bloque({ n, titulo, children }: { n: number; titulo: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border p-5" style={{ borderColor: "rgba(245,243,238,0.14)", background: "#17150F" }}>
      <div className="mb-4 flex items-center gap-2.5">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg text-sm font-extrabold"
          style={{ background: "#E9A90F", color: "#241C04" }}>{n}</span>
        <h2 className="text-base font-bold">{titulo}</h2>
      </div>
      <div className="space-y-3.5">{children}</div>
    </section>
  );
}

function Fila({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-3.5 sm:grid-cols-2">{children}</div>;
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide opacity-60">{label}</span>
      {children}
    </label>
  );
}
