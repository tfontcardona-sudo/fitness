import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

/**
 * EL CUESTIONARIO DE PROFESSIONAL (Centre Salut & Fitness).
 *
 * Es una pantalla APARTE de la de DQR a propósito, no una variante con
 * `if`s: el dueño pidió que «la estructura y las preguntas no se parezcan en
 * nada a DQR», y con un solo formulario parametrizado cada retoque de un
 * negocio arriesga el del otro. El sistema interno SÍ es el mismo — escribe
 * contra `POST /api/p/{token}/anamnesis`, el mismo contrato, la misma ficha y
 * el mismo motor de cálculo.
 *
 * Qué lo hace distinto:
 * · CORTO. El centro ve al cliente en la sala: lo que no hace falta por
 *   escrito para planificar se pregunta en persona. Cuatro bloques y firmar.
 * · SU LENGUAJE. Un gimnasio de barrio no habla de «anamnesis», ni de
 *   «recomposición corporal», ni de «patrón dietético».
 * · NEGRO Y DORADO, la identidad del centro: fondo negro, filete dorado,
 *   tipografía amplia y nada de color de más.
 *
 * Lo que NO cambia, y no puede cambiar: las preguntas de las que salen los
 * números (sexo, edad, altura, peso, objetivo, nivel, días y sitio de entreno)
 * y las de seguridad (lesiones, patologías, medicación, alergias). Quitar una
 * sola no simplifica el formulario: rompe el plan.
 */

/* ------------------------------------------------------------- contrato --- */

interface Ficha {
  sex: "" | "male" | "female";
  birth_date: string;
  height_cm: string;
  start_weight_kg: string;
  body_fat_pct: string;
  goal_type: string;
  goal_weight_kg: string;
  priority_zones: string;
  level: string;
  training_days: string;
  session_max_min: string;
  training_place: string;
  daily_activity_level: string;
  injuries_notes: string;
  medical_notes: string;
  medication_notes: string;
  current_supplements: string;
  food_allergies: string;
  food_dislikes: string;
  diet_pattern: string;
  diet_mode: string;
  meals_per_day: string;
  lifestyle_notes: string;
}

const VACIA: Ficha = {
  sex: "", birth_date: "", height_cm: "", start_weight_kg: "", body_fat_pct: "",
  goal_type: "", goal_weight_kg: "", priority_zones: "",
  level: "", training_days: "", session_max_min: "60", training_place: "gym",
  daily_activity_level: "", injuries_notes: "", medical_notes: "",
  medication_notes: "", current_supplements: "", food_allergies: "",
  food_dislikes: "", diet_pattern: "", diet_mode: "flexible_7",
  meals_per_day: "", lifestyle_notes: "",
};

/** Las opciones, dichas como las diría alguien en el mostrador. */
const METAS = [
  ["fat_loss", "Bajar grasa", "marcar más y verme mejor"],
  ["muscle_gain", "Ganar músculo", "más volumen y más fuerza"],
  ["recomp", "Las dos cosas", "bajar grasa sin perder músculo"],
  ["maintenance", "Mantenerme y coger el hábito", "constancia y salud"],
  ["injury_recovery", "Volver después de una lesión", "sin forzar la zona"],
] as const;

const EXPERIENCIA = [
  ["beginner", "Empiezo ahora", "menos de un año"],
  ["intermediate", "Llevo un tiempo", "entre uno y tres años"],
  ["advanced", "Entreno desde hace años", "más de tres"],
] as const;

const SITIOS = [
  ["gym", "En el centro"],
  ["home", "En casa (viajo o no siempre puedo venir)"],
] as const;

const ACTIVIDAD = [
  ["sedentary", "Sentado casi todo el día"],
  ["light", "De pie a ratos, ando algo"],
  ["active", "En movimiento la mayor parte del día"],
  ["very_active", "Trabajo físico duro"],
] as const;

const COMIDA = [
  ["flexible_7", "Con opciones para elegir", "varias alternativas en cada comida"],
  ["strict", "Dime exactamente qué comer", "el menú cerrado de cada día"],
] as const;

const PATRONES = [
  ["", "Como de todo"],
  ["vegetariano", "Vegetariano"],
  ["vegano", "Vegano"],
  ["pescetariano", "Pescetariano"],
  ["sin_cerdo", "Sin cerdo"],
  ["halal", "Halal"],
  ["kosher", "Kosher"],
] as const;

const BLOQUES = ["Tus datos", "Tu meta", "Tu entreno", "Salud y comida", "Firmar"] as const;

/* ---------------------------------------------------------- borrador ------ */
// Clave POR TOKEN: en un móvil compartido, lo que escribe uno no puede
// aparecerle a otro (misma regla que el resto del portal).
const claveBorrador = (token?: string) =>
  `pf.cuestionario.${(token ?? "").slice(0, 16)}`;
const TTL_MS = 30 * 24 * 3600 * 1000;

function guardar(token: string | undefined, ficha: Ficha, bloque: number,
                 extra: Record<string, string>): void {
  try {
    localStorage.setItem(claveBorrador(token),
      JSON.stringify({ ficha, bloque, extra, ts: Date.now() }));
  } catch { /* modo privado: se pierde, como antes de existir */ }
}
function borrar(token?: string): void {
  try { localStorage.removeItem(claveBorrador(token)); } catch { /* nada */ }
}
function recuperar(token?: string): { ficha: Ficha; bloque: number; extra: Record<string, string> } | null {
  try {
    const raw = localStorage.getItem(claveBorrador(token));
    if (!raw) return null;
    const d = JSON.parse(raw);
    if (!d?.ficha || Date.now() - (d.ts ?? 0) > TTL_MS) return null;
    return { ficha: { ...VACIA, ...d.ficha }, bloque: Number(d.bloque) || 0,
             extra: (d.extra && typeof d.extra === "object") ? d.extra : {} };
  } catch { return null; }
}

const num = (v: string) => Number(String(v).replace(",", "."));
/** ¿Esto es un número que se puede usar? Un campo de texto admite «sesenta» y
 *  un NaN enviado al backend vuelve como un 422 que no dice nada útil. */
const esNumero = (v: string) => v.trim() !== "" && Number.isFinite(num(v));
const lista = (v: string) =>
  v.split(",").map((x) => x.trim()).filter(Boolean).slice(0, 30);

const CAMPOS_ES: Record<string, string> = {
  sex: "el sexo", birth_date: "la fecha de nacimiento", height_cm: "la altura",
  start_weight_kg: "el peso", body_fat_pct: "el % de grasa",
  goal_type: "el objetivo", goal_weight_kg: "el peso que buscas",
  level: "la experiencia", training_days: "los días de entreno",
  session_max_min: "la duración de la sesión", training_place: "dónde entrenas",
  diet_mode: "cómo quieres la dieta",
};

interface Pregunta { key: string; label: string; placeholder?: string }

/* ================================================================= vista === */

export default function AnamnesisProfesional({ token }: { token?: string }) {
  const guardado = useMemo(() => recuperar(token), [token]);
  const [ficha, setFicha] = useState<Ficha>(guardado?.ficha ?? VACIA);
  const [bloque, setBloque] = useState(guardado?.bloque ?? 0);
  const [extra, setExtra] = useState<Record<string, string>>(guardado?.extra ?? {});
  const [preguntas, setPreguntas] = useState<Pregunta[]>([]);
  const [zonasVisible, setZonasVisible] = useState(true);
  const [logo, setLogo] = useState<string | null>(null);
  const [nombre, setNombre] = useState("");
  const [consiento, setConsiento] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hecho, setHecho] = useState(false);
  const [enlaceMalo, setEnlaceMalo] = useState(false);
  const arriba = useRef<HTMLDivElement>(null);

  const set = (parche: Partial<Ficha>) => setFicha((f) => ({ ...f, ...parche }));

  useEffect(() => {
    fetch(`/api/p/${token}`)
      .then((r) => (r.status === 404 ? (setEnlaceMalo(true), null) : r.json()))
      .then((st) => {
        if (!st) return;
        if (st.anamnesis_done) { borrar(token); setHecho(true); }
        setLogo(st.logo_url ?? null);
        setNombre(st.first_name ?? "");
        if (Array.isArray(st.extra_questions)) setPreguntas(st.extra_questions);
        if (Array.isArray(st.optional_blocks))
          setZonasVisible(st.optional_blocks.includes("priority_zones"));
      })
      .catch(() => { /* el backend re-valida al enviar */ });
    // Pre-relleno con lo que el centro ya apuntó al darle de alta: solo se
    // escribe donde el cliente aún no ha puesto nada.
    fetch(`/api/p/${token}/anamnesis/prefill`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setFicha((f) => {
          const out = { ...f };
          const pon = (k: keyof Ficha, v: unknown) => {
            if (v !== null && v !== undefined && String(v) !== "" && !out[k])
              (out[k] as string) = String(v);
          };
          pon("sex", d.sex); pon("birth_date", d.birth_date);
          pon("height_cm", d.height_cm); pon("start_weight_kg", d.start_weight_kg);
          pon("goal_type", d.goal_type); pon("level", d.level);
          pon("training_days", d.training_days);
          pon("training_place", d.training_place);
          return out;
        });
      })
      .catch(() => { /* opcional */ });
  }, [token]);

  useEffect(() => { guardar(token, ficha, bloque, extra); }, [token, ficha, bloque, extra]);
  useEffect(() => { arriba.current?.scrollIntoView({ block: "start" }); }, [bloque]);

  /** Lo que falta en cada bloque, dicho para que se pueda arreglar. */
  const falta: (string | null)[] = [
    !ficha.sex ? "Marca si eres hombre o mujer"
      : !ficha.birth_date ? "Falta tu fecha de nacimiento"
      : !esNumero(ficha.height_cm) ? "Falta tu altura, en centímetros"
      : !esNumero(ficha.start_weight_kg) ? "Falta tu peso, en kilos"
      : ficha.body_fat_pct && !esNumero(ficha.body_fat_pct)
        ? "El % de grasa tiene que ser un número (o déjalo en blanco)" : null,
    !ficha.goal_type ? "Elige qué quieres conseguir"
      : ficha.goal_weight_kg && !esNumero(ficha.goal_weight_kg)
        ? "El peso que buscas tiene que ser un número (o déjalo en blanco)" : null,
    !ficha.level ? "Dinos cuánto llevas entrenando"
      : !ficha.training_days ? "¿Cuántos días a la semana puedes entrenar?"
      : !ficha.training_place ? "¿Dónde vas a entrenar?" : null,
    !ficha.diet_mode ? "Elige cómo prefieres la dieta" : null,
    !consiento ? "Marca la casilla para poder enviarlo" : null,
  ];

  async function enviar() {
    if (enviando || falta[4]) return;
    setEnviando(true);
    setError(null);
    const cuerpo = {
      sex: ficha.sex,
      birth_date: ficha.birth_date,
      height_cm: num(ficha.height_cm),
      start_weight_kg: num(ficha.start_weight_kg),
      body_fat_pct: esNumero(ficha.body_fat_pct) ? num(ficha.body_fat_pct) : null,
      goal_type: ficha.goal_type,
      goal_weight_kg: esNumero(ficha.goal_weight_kg) ? num(ficha.goal_weight_kg) : null,
      priority_zones: ficha.priority_zones.trim() || null,
      level: ficha.level,
      training_days: +ficha.training_days,
      session_max_min: +ficha.session_max_min,
      training_place: ficha.training_place,
      equipment: [],
      daily_activity_level: ficha.daily_activity_level || null,
      injuries_notes: ficha.injuries_notes.trim() || null,
      medical_notes: ficha.medical_notes.trim() || null,
      medication_notes: ficha.medication_notes.trim() || null,
      current_supplements: ficha.current_supplements.trim() || null,
      diet_mode: ficha.diet_mode,
      diet_pattern: ficha.diet_pattern || null,
      meals_per_day: ficha.meals_per_day ? +ficha.meals_per_day : null,
      food_allergies: lista(ficha.food_allergies),
      food_dislikes: lista(ficha.food_dislikes),
      food_likes: [],
      lifestyle_notes: ficha.lifestyle_notes.trim() || null,
      consent_accepted: true,
      extra_answers: Object.fromEntries(
        preguntas.map((q) => [q.key, (extra[q.key] ?? "").trim()])
          .filter(([, v]) => v),
      ),
    };
    try {
      const r = await fetch(`/api/p/${token}/anamnesis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
      });
      if (!r.ok) {
        let msg = "No se ha podido enviar. Revisa los datos e inténtalo otra vez.";
        try {
          const d = await r.json();
          if (typeof d?.detail === "string") msg = d.detail;
          else if (Array.isArray(d?.detail) && d.detail[0]) {
            const d0 = d.detail[0];
            const campo = CAMPOS_ES[String(d0?.loc?.[d0.loc.length - 1])] ?? "un dato";
            msg = `Revisa ${campo}: ${d0?.msg ?? "no es válido"}`;
          }
        } catch { /* sin cuerpo */ }
        throw new Error(msg);
      }
      borrar(token);
      setHecho(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se ha podido enviar.");
    } finally {
      setEnviando(false);
    }
  }

  if (enlaceMalo) {
    return (
      <Marco logo={logo}>
        <h1 className="pf-h1">Este enlace ya no sirve</h1>
        <p className="pf-p">
          Puede que se haya renovado. Escríbenos y te mandamos uno nuevo.
        </p>
      </Marco>
    );
  }

  if (hecho) {
    return (
      <Marco logo={logo}>
        <div className="pf-ok"><CheckCircle2 size={34} /></div>
        <h1 className="pf-h1">Recibido{nombre ? `, ${nombre}` : ""}</h1>
        <p className="pf-p">
          Ya tenemos lo que necesitamos. Preparamos tu plan y te avisamos en cuanto
          esté listo — cualquier duda, nos la cuentas en el centro.
        </p>
      </Marco>
    );
  }

  const ultimo = bloque === BLOQUES.length - 1;

  return (
    <Marco logo={logo}>
      <div ref={arriba} />
      <p className="pf-eyebrow">Cuestionario inicial</p>
      <h1 className="pf-h1">
        {nombre ? `Empezamos, ${nombre}` : "Empezamos"}
      </h1>
      <p className="pf-p">
        Cinco minutos. Con esto preparamos tu dieta y tu entrenamiento a tu medida.
      </p>

      {/* Camino: en qué bloque vas y cuántos quedan. */}
      <ol className="pf-pasos" aria-label="Progreso">
        {BLOQUES.map((b, i) => (
          <li key={b} className="pf-paso" data-estado={
            i === bloque ? "actual" : i < bloque ? "hecho" : "pendiente"}>
            <span className="pf-paso-n">{i + 1}</span>
            <span className="pf-paso-t">{b}</span>
          </li>
        ))}
      </ol>

      <section className="pf-tarjeta">
        {bloque === 0 && (
          <>
            <Titulo n="01" t="Tus datos" s="Lo justo para calcular tus cifras." />
            <Eleccion label="¿Hombre o mujer?" valor={ficha.sex}
              opciones={[["male", "Hombre"], ["female", "Mujer"]]}
              onPick={(v) => set({ sex: v as Ficha["sex"] })} />
            <div className="pf-fila">
              <Campo label="Fecha de nacimiento" tipo="date" valor={ficha.birth_date}
                onChange={(v) => set({ birth_date: v })} />
              <Campo label="Altura (cm)" tipo="number" valor={ficha.height_cm}
                onChange={(v) => set({ height_cm: v })} placeholder="175" />
            </div>
            <div className="pf-fila">
              <Campo label="Peso hoy (kg)" tipo="number" valor={ficha.start_weight_kg}
                onChange={(v) => set({ start_weight_kg: v })} placeholder="78,5" />
              <Campo label="% de grasa (si lo sabes)" tipo="number"
                valor={ficha.body_fat_pct} onChange={(v) => set({ body_fat_pct: v })}
                placeholder="Opcional" />
            </div>
            <Campo label="¿Cómo es tu día a día fuera del gimnasio?" tipo="select"
              valor={ficha.daily_activity_level}
              onChange={(v) => set({ daily_activity_level: v })}
              opciones={[["", "Elige una"], ...ACTIVIDAD.map(([v, t]) => [v, t] as [string, string])]} />
          </>
        )}

        {bloque === 1 && (
          <>
            <Titulo n="02" t="Tu meta" s="Qué quieres conseguir con nosotros." />
            <Tarjetas valor={ficha.goal_type} opciones={METAS}
              onPick={(v) => set({ goal_type: v })} />
            <Campo label="¿Tienes un peso en mente? (kg)" tipo="number"
              valor={ficha.goal_weight_kg} onChange={(v) => set({ goal_weight_kg: v })}
              placeholder="Opcional — si no, lo marcamos juntos" />
            {zonasVisible && (
              <Campo label="¿Alguna zona que quieras trabajar más?" tipo="text"
                valor={ficha.priority_zones}
                onChange={(v) => set({ priority_zones: v })}
                placeholder="Ej.: espalda y piernas" />
            )}
            {preguntas.filter((q) => q.key === "obstaculo").map((q) => (
              <Campo key={q.key} label={q.label} tipo="area"
                valor={extra[q.key] ?? ""}
                onChange={(v) => setExtra((e) => ({ ...e, [q.key]: v }))}
                placeholder={q.placeholder} />
            ))}
          </>
        )}

        {bloque === 2 && (
          <>
            <Titulo n="03" t="Tu entreno" s="Con qué contamos de verdad cada semana." />
            <Tarjetas valor={ficha.level} opciones={EXPERIENCIA}
              onPick={(v) => set({ level: v })} />
            <div className="pf-fila">
              <Campo label="Días por semana" tipo="select" valor={ficha.training_days}
                onChange={(v) => set({ training_days: v })}
                opciones={[["", "Elige"], ["2", "2 días"], ["3", "3 días"],
                           ["4", "4 días"], ["5", "5 días"], ["6", "6 días"]]} />
              <Campo label="Tiempo por sesión" tipo="select" valor={ficha.session_max_min}
                onChange={(v) => set({ session_max_min: v })}
                opciones={[["45", "45 minutos"], ["60", "1 hora"],
                           ["75", "1 hora y cuarto"], ["90", "1 hora y media"]]} />
            </div>
            <Eleccion label="¿Dónde vas a entrenar?" valor={ficha.training_place}
              opciones={SITIOS.map(([v, t]) => [v, t] as [string, string])}
              onPick={(v) => set({ training_place: v })} />
            {preguntas.filter((q) => q.key === "experiencia" || q.key === "disponibilidad")
              .map((q) => (
                <Campo key={q.key} label={q.label} tipo="text"
                  valor={extra[q.key] ?? ""}
                  onChange={(v) => setExtra((e) => ({ ...e, [q.key]: v }))}
                  placeholder={q.placeholder} />
              ))}
          </>
        )}

        {bloque === 3 && (
          <>
            <Titulo n="04" t="Salud y comida"
              s="Esto es lo que nos deja plantear algo seguro. Si no hay nada, déjalo en blanco." />
            <Campo label="Lesiones, molestias u operaciones" tipo="area"
              valor={ficha.injuries_notes} onChange={(v) => set({ injuries_notes: v })}
              placeholder="Hombro, rodilla, espalda… y qué te molesta al hacerlo" />
            <Campo label="Problemas de salud que debamos saber" tipo="area"
              valor={ficha.medical_notes} onChange={(v) => set({ medical_notes: v })}
              placeholder="Tensión, tiroides, diabetes, digestivo…" />
            <div className="pf-fila">
              <Campo label="Medicación" tipo="text" valor={ficha.medication_notes}
                onChange={(v) => set({ medication_notes: v })} placeholder="Cuál y para qué" />
              <Campo label="Suplementos que tomas" tipo="text"
                valor={ficha.current_supplements}
                onChange={(v) => set({ current_supplements: v })} placeholder="Si tomas alguno" />
            </div>
            <Campo label="Alergias o intolerancias" tipo="text"
              valor={ficha.food_allergies} onChange={(v) => set({ food_allergies: v })}
              placeholder="Separadas por comas: lactosa, frutos secos…" />
            <Campo label="Lo que no te vas a comer" tipo="text"
              valor={ficha.food_dislikes} onChange={(v) => set({ food_dislikes: v })}
              placeholder="Separado por comas: pescado azul, brócoli…" />
            <Campo label="¿Sigues alguna pauta?" tipo="select" valor={ficha.diet_pattern}
              onChange={(v) => set({ diet_pattern: v })}
              opciones={PATRONES.map(([v, t]) => [v, t] as [string, string])} />
            <Tarjetas valor={ficha.diet_mode} opciones={COMIDA}
              onPick={(v) => set({ diet_mode: v })} />
            <Campo label="¿Cuántas comidas al día te van bien?" tipo="select"
              valor={ficha.meals_per_day} onChange={(v) => set({ meals_per_day: v })}
              opciones={[["", "Decidid vosotros"], ["3", "3"], ["4", "4"], ["5", "5"]]} />
            <Campo label="Horarios, turnos o cualquier cosa que debamos tener en cuenta"
              tipo="area" valor={ficha.lifestyle_notes}
              onChange={(v) => set({ lifestyle_notes: v })}
              placeholder="Trabajo a turnos, como fuera de casa, duermo poco…" />
          </>
        )}

        {bloque === 4 && (
          <>
            <Titulo n="05" t="Firmar y enviar" s="Un último paso y lo tenemos." />
            <div className="pf-consent">
              <p className="pf-p">
                Nos das permiso para tratar estos datos —incluidos los de salud— con
                el único fin de prepararte y ajustarte tu plan. Puedes pedirnos que
                los borremos cuando quieras.
              </p>
              <label className="pf-check">
                <input type="checkbox" checked={consiento}
                  onChange={(e) => setConsiento(e.target.checked)} />
                <span>He leído y acepto.</span>
              </label>
            </div>
            <ul className="pf-resumen">
              <li><b>{ficha.start_weight_kg || "—"} kg</b> · {ficha.height_cm || "—"} cm</li>
              <li>{METAS.find(([v]) => v === ficha.goal_type)?.[1] ?? "Sin objetivo"}</li>
              <li>{ficha.training_days || "—"} días · {ficha.session_max_min} min</li>
            </ul>
            {error && <p className="pf-error" role="alert">{error}</p>}
          </>
        )}

        {falta[bloque] && (
          <p className="pf-falta">{falta[bloque]}</p>
        )}

        <div className="pf-botonera">
          <button type="button" className="pf-btn pf-btn--ghost"
            onClick={() => setBloque((b) => Math.max(0, b - 1))}
            disabled={bloque === 0}>
            <ArrowLeft size={16} /> Atrás
          </button>
          {!ultimo ? (
            <button type="button" className="pf-btn pf-btn--oro"
              onClick={() => setBloque((b) => Math.min(BLOQUES.length - 1, b + 1))}
              disabled={!!falta[bloque]}>
              Seguir <ArrowRight size={16} />
            </button>
          ) : (
            <button type="button" className="pf-btn pf-btn--oro"
              onClick={() => void enviar()} disabled={enviando || !!falta[4]}>
              {enviando ? <Loader2 size={16} className="pf-girar" /> : null}
              {enviando ? "Enviando…" : "Enviar"}
            </button>
          )}
        </div>
      </section>
    </Marco>
  );
}

/* ------------------------------------------------------------- piezas ----- */

function Marco({ children, logo }: { children: React.ReactNode; logo: string | null }) {
  return (
    <div className="pf-root">
      <div className="pf-hoja">
        <header className="pf-cab">
          {logo
            ? <img src={logo} alt="" className="pf-logo" />
            : <span className="pf-marca">PROFESSIONAL</span>}
          <span className="pf-cab-sub">Centre Salut &amp; Fitness</span>
        </header>
        {children}
        <footer className="pf-pie">Professional · Centre Salut &amp; Fitness · Girona</footer>
      </div>
    </div>
  );
}

function Titulo({ n, t, s }: { n: string; t: string; s: string }) {
  return (
    <div className="pf-titulo">
      <span className="pf-titulo-n">{n}</span>
      <div>
        <h2 className="pf-h2">{t}</h2>
        <p className="pf-sub">{s}</p>
      </div>
    </div>
  );
}

function Campo({ label, tipo, valor, onChange, placeholder, opciones }: {
  label: string;
  tipo: "text" | "number" | "date" | "area" | "select";
  valor: string;
  onChange: (v: string) => void;
  placeholder?: string;
  opciones?: [string, string][];
}) {
  const id = `pf-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <label className="pf-campo" htmlFor={id}>
      <span className="pf-label">{label}</span>
      {tipo === "area" ? (
        <textarea id={id} className="pf-input pf-area" value={valor}
          placeholder={placeholder} rows={3}
          onChange={(e) => onChange(e.target.value)} />
      ) : tipo === "select" ? (
        <select id={id} className="pf-input" value={valor}
          onChange={(e) => onChange(e.target.value)}>
          {(opciones ?? []).map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </select>
      ) : (
        // ⚠️ Los decimales NUNCA en un <input type="number">: en español se
        // escribe «63,5» y el navegador rechaza la coma EN SILENCIO — el campo
        // se queda vacío y el cliente no entiende por qué no le deja seguir.
        // Texto + inputMode="decimal": teclado numérico en el móvil y coma
        // admitida (es lo mismo que hace el cuestionario de DQR).
        <input id={id} className="pf-input"
          type={tipo === "number" ? "text" : tipo}
          inputMode={tipo === "number" ? "decimal" : undefined}
          value={valor} placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)} />
      )}
    </label>
  );
}

/** Dos o tres opciones cortas, en línea. */
function Eleccion({ label, valor, opciones, onPick }: {
  label: string; valor: string; opciones: [string, string][];
  onPick: (v: string) => void;
}) {
  return (
    <div className="pf-campo" role="group" aria-label={label}>
      <span className="pf-label">{label}</span>
      <div className="pf-eleccion">
        {opciones.map(([v, t]) => (
          <button key={v} type="button" className="pf-opcion"
            aria-pressed={valor === v} data-activa={valor === v}
            onClick={() => onPick(v)}>
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Opciones con explicación: se eligen leyendo, no adivinando. */
function Tarjetas({ valor, opciones, onPick }: {
  valor: string;
  opciones: readonly (readonly [string, string, string])[];
  onPick: (v: string) => void;
}) {
  return (
    <div className="pf-tarjetas">
      {opciones.map(([v, t, s]) => (
        <button key={v} type="button" className="pf-opcion pf-opcion--ancha"
          aria-pressed={valor === v} data-activa={valor === v}
          onClick={() => onPick(v)}>
          <span className="pf-opcion-t">{t}</span>
          <span className="pf-opcion-s">{s}</span>
        </button>
      ))}
    </div>
  );
}
