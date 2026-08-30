import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, BellRing, ChevronRight, MessageCircle, Pencil, Smartphone, ClipboardCheck, Trash2, CreditCard } from "lucide-react";
import { api, keepIfSame, REFRESH_MS } from "../lib/api";
import { openWhatsApp, waPhone } from "../lib/whatsapp";
import type { PaymentsListOut, ClientOut } from "../types";
import {
  ConfirmDialog,
  PageLoader,
  StatusBadge,
  useToast,
} from "../components/ui";
import { Avatar } from "./DashboardPage";
import { ClientSummaryTab } from "../components/ClientSummaryTab";
import { ClientAnamnesisTab } from "../components/ClientAnamnesisTab";
import { ClientDocuments } from "../components/ClientDocuments";
import { MarcadorDeAncla } from "../components/Pins";
import { ancla, irYMarcar } from "../lib/anchors";
import { copiarConAviso } from "../lib/clipboard";
import { ClientPlanPanel } from "../components/ClientPlanPanel";
import { ClientFeedbackTab } from "../components/ClientFeedbackTab";
import { ClientHistoryTab } from "../components/ClientHistoryTab";
import { ClientTrackingTab } from "../components/ClientTrackingTab";
import { ageFrom, formatDate, GOAL_LABEL, LEVEL_LABEL, PLACE_LABEL, relativeDays } from "../lib/format";
import { BILLING_PERIODS, PACKAGES, PACKAGE_ORDER, billingLabel, pkg } from "../lib/packages";

type Tab = "resumen" | "anamnesis" | "planificacion" | "seguimiento" | "feedback" | "historial";

export default function ClientProfilePage() {
  const { id } = useParams();
  const clientId = Number(id);
  const toast = useToast();
  const navigate = useNavigate();
  const [client, setClient] = useState<ClientOut | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[])
    .includes(searchParams.get("tab") as Tab) ? (searchParams.get("tab") as Tab) : "resumen";
  const [tab, setTab] = useState<Tab>(initialTab);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);
  const [payUrl, setPayUrl] = useState<string | null>(null);
  // Qué hará ese enlace al abrirlo, dicho por el backend (el coach lo mandaba
  // sin saber si cobraba o si el cliente acabaría en "pago recibido").
  const [payNote, setPayNote] = useState<string | null>(null);
  const [payState, setPayState] = useState<string | null>(null);
  const [anamnesisUrl, setAnamnesisUrl] = useState<string | null>(null);
  // Aviso "revisión cerrada": solo mientras el feedback de la última revisión
  // NO exista todavía. En cuanto el coach lo genera, el aviso desaparece.
  const [feedbackPending, setFeedbackPending] = useState(false);
  // La pestaña Anamnesis tiene edición local; avisamos si se sale con cambios sin
  // guardar (el panel se re-monta al cambiar de pestaña y perdería el borrador).
  const [anamnesisDirty, setAnamnesisDirty] = useState(false);
  // Editor de PLAN abierto: cambiar de pestaña re-monta el panel y perdería
  // todos los retoques. Mismo guard que la anamnesis.
  const [planEditing, setPlanEditing] = useState(false);

  // Ancla a marcar al llegar (?ir=nutricion.comida.2): la pone el aviso que se
  // pulsó. Se conserva mientras el recordatorio siga vivo; al cambiar de
  // pestaña a mano se suelta (ya no estás en el sitio que se te señaló).
  const ir = searchParams.get("ir");

  /** Aplica la pestaña, con sus guardas de borrador sin guardar, SIN tocar la
   *  URL. Devuelve si el cambio se aceptó. */
  function aplicarTab(next: Tab): boolean {
    if (next === tab) return false;
    if (tab === "anamnesis" && anamnesisDirty &&
        !window.confirm("Tienes cambios sin guardar en la anamnesis. ¿Descartarlos?")) {
      return false;
    }
    if (tab === "planificacion" && planEditing &&
        !window.confirm("Tienes el editor del plan abierto con cambios sin guardar. ¿Descartarlos?")) {
      return false;
    }
    if (tab === "anamnesis") setAnamnesisDirty(false);
    if (tab === "planificacion") setPlanEditing(false);
    setTab(next);
    return true;
  }

  /** Clic MANUAL en una pestaña. Además de aplicarla reescribe la URL, y ahí
   *  SÍ se suelta el ancla: ya no estás en el sitio que se te señaló.
   *
   *  Esto NO lo puede usar el efecto que sigue a la URL: al reescribirla
   *  borraba el `?ir=` en el mismo instante, así que pulsar un aviso estando
   *  YA dentro de la ficha del cliente cambiaba de pestaña sin marcar nada
   *  — el camino más común de todos. */
  function changeTab(next: Tab) {
    if (!aplicarTab(next)) return;
    // La URL refleja la pestaña activa: recargar o compartir el enlace vuelve
    // a la misma pestaña. `replace` para no llenar el historial.
    setSearchParams({ tab: next }, { replace: true });
  }

  // Cerrar/recargar la pestaña del navegador con un borrador abierto: el aviso
  // nativo del navegador evita perder media hora de edición por un despiste.
  useEffect(() => {
    if (!anamnesisDirty && !planEditing) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [anamnesisDirty, planEditing]);

  const [loadError, setLoadError] = useState(false);
  const load = useCallback(() => {
    api.getClient(clientId)
      // keepIfSame: solo cambia la referencia (y re-renderiza) si los datos han
      // cambiado de verdad. Evita el parpadeo y el re-fetch de "Dieta"/feedback
      // cada 3 s cuando la ficha no ha cambiado.
      .then((c) => { setClient((prev) => keepIfSame(prev, c)); setLoadError(false); })
      .catch(() => setLoadError(true));
  }, [clientId]);

  useEffect(load, [load]);

  // Recarga EXPLÍCITA tras una acción del coach (editar/adaptar/generar plan,
  // guardar anamnesis, subir documento…): además de refrescar la ficha, sube un
  // contador que re-sincroniza la "Dieta" y el aviso de feedback aunque la fila
  // del cliente no haya cambiado (el plan vive aparte). El polling de 3 s NO sube
  // este contador, así que no re-consulta esos datos si nada cambió.
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => {
    load();
    setReloadKey((k) => k + 1);
  }, [load]);

  // Refresco cada 3 s (pestaña visible): la ficha siempre al día. Se PAUSA
  // mientras se edita la anamnesis (borrador sin guardar): un refresco en medio
  // de la edición sería una fuente de desincronización y despiste.
  useEffect(() => {
    if (anamnesisDirty) return;
    const t = window.setInterval(() => {
      if (!document.hidden) load();
    }, REFRESH_MS);
    return () => window.clearInterval(t);
  }, [load, anamnesisDirty]);

  // La pestaña SIGUE a la URL: navegar desde una alerta (o el botón atrás)
  // cambia de pestaña aunque ya estemos en el perfil de este cliente.
  // Pasa por changeTab: el guard de borradores sin guardar aplica TAMBIÉN aquí
  // (llegar desde la campana con ?tab= descartaba la anamnesis sin preguntar).
  useEffect(() => {
    const t = searchParams.get("tab") as Tab | null;
    const valid: Tab[] = ["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"];
    // `aplicarTab`, NO `changeTab`: reescribir la URL aquí borraría el `?ir=`
    // del aviso que acaba de traernos.
    if (t && valid.includes(t)) aplicarTab(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    if (client?.status !== "review_pending") {
      setFeedbackPending(false);
      return;
    }
    api.listPeriods(clientId)
      .then((ps: any[]) => {
        const latest = ps
          .filter((p) => p.status !== "open")
          .reduce<any>((a, b) => (!a || b.period_index > a.period_index ? b : a), null);
        setFeedbackPending(latest != null && !latest.feedback_id);
      })
      .catch(() => setFeedbackPending(true));
  }, [client, clientId, reloadKey]);

  // Precargamos el enlace del portal con el ORIGEN actual del navegador (en dev
  // :5173, en prod el dominio) para poder abrirlo de forma síncrona (sin que el
  // navegador bloquee la pestaña) y que el enlace funcione siempre.
  useEffect(() => {
    api.portalLink(clientId)
      .then((l) => {
        setPortalUrl(`${window.location.origin}/p/${l.portal_token}`);
        // El enlace de PAGO lo da el backend: lleva el dominio público
        // oficial y dice qué hará al abrirlo (cobrar, renovar o no cobrar
        // porque ya pagó). Antes se armaba aquí y se mandaba a ciegas.
        api.clientPayLink(clientId)
          .then((pl) => { setPayUrl(pl.url); setPayNote(pl.note); setPayState(pl.state); })
          .catch(() => { setPayUrl(api.payLinkUrl(l.portal_token)); });
        setAnamnesisUrl(`${window.location.origin}/anamnesis/${l.portal_token}`);
      })
      .catch(() => { setPortalUrl(null); setPayUrl(null); setAnamnesisUrl(null); });
  }, [clientId]);

  // "Dieta" de la info básica = la dieta GENERADA con IA (kcal y macros del
  // plan activo). Hasta que no hay planificación, el apartado queda vacío.
  // Depende de `client` (objeto nuevo en cada load()): así CUALQUIER acción
  // que llame a onClientChanged (generar, adaptar, editar…) la resincroniza,
  // aunque la fila del cliente no cambie.
  const [planDiet, setPlanDiet] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    // LIGERO: la línea "Dieta" solo necesita kcal, macros y el nº de tomas.
    api.listPlans(clientId, { ligero: true })
      .then((plans: any[]) => {
        if (!alive) return;
        const active = plans.find((p) => p.status === "published");
        const n = active?.nutrition_json;
        if (n?.target_kcal) {
          const m = n.macros ?? {};
          const nMeals = Array.isArray(n.meals) ? n.meals.length : null;
          setPlanDiet(
            `${Math.round(n.target_kcal)} kcal · P${Math.round(m.protein_g ?? 0)} ` +
            `C${Math.round(m.carbs_g ?? 0)} G${Math.round(m.fat_g ?? 0)}` +
            (nMeals ? ` · ${nMeals} comidas/día` : ""),
          );
        } else setPlanDiet(null);
      })
      .catch(() => setPlanDiet(null));
    return () => { alive = false; };
  }, [clientId, client, reloadKey]);

  function openPortal() {
    if (!portalUrl) return;
    window.open(portalUrl, "_blank", "noopener");
    void copiarConAviso(portalUrl, toast, "Enlace del portal copiado y abierto");
  }

  async function regenerate() {
    if (!client) return;
    setConfirmRegen(false);
    try {
      await api.regeneratePortalToken(client.id);
      toast.push("Enlace regenerado. El anterior ya no funciona.");
    } catch {
      toast.push("No se pudo regenerar", "error");
    }
  }

  async function deleteClient() {
    if (!client || deleting) return;
    setDeleting(true);
    try {
      await api.deleteClient(client.id, client.full_name);
      setConfirmDelete(false);
      toast.push(`${client.full_name} eliminado definitivamente`);
      navigate("/clientes");
    } catch {
      toast.push("No se pudo borrar el cliente", "error");
      setDeleting(false);
    }
  }

  if (loadError && client === null) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-16 text-center">
        <p className="text-lg font-semibold text-zinc-200">No se pudo cargar el cliente</p>
        <p className="mt-1 text-sm text-zinc-500">Puede que se haya eliminado o que el enlace no sea válido.</p>
        <Link to="/clientes" className="btn btn-ghost mt-4 inline-flex">Volver a Clientes</Link>
      </div>
    );
  }
  if (client === null) return <PageLoader />;

  const age = ageFrom(client.birth_date);
  // Paquete solo-nutrición (Start): sin nada de entreno en la ficha.
  const hasTraining = pkg(client.package_tier).hasTraining;

  return (
    <div className="mx-auto max-w-6xl px-6 py-6">
      {/* Marca el elemento exacto del que hablaba el aviso y le pega la nota de
          cómo se arregla. Si el problema se resuelve, la marca se va sola. */}
      <MarcadorDeAncla clientId={clientId} target={ir} />
      <Link to="/clientes" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={15} /> Clientes
      </Link>

      {/* Notificación: el cliente cerró su período → toca generar feedback.
          Se oculta en cuanto el feedback ya está generado. */}
      {client.status === "review_pending" && feedbackPending && (
        <button
          onClick={() => { changeTab("feedback"); void irYMarcar("feedback.generar"); }}
          className="mt-4 flex w-full flex-wrap items-center justify-between gap-3 rounded-xl border p-3.5 text-left transition-transform active:scale-[0.995]"
          style={{ borderColor: "var(--brand-accent)", background: "color-mix(in srgb, var(--brand-accent) 10%, transparent)" }}
        >
          <span className="flex items-center gap-2.5 text-sm text-zinc-200">
            <BellRing size={18} style={{ color: "var(--brand-accent)" }} />
            <span><b>El cliente ha cerrado su período.</b> Revisa los datos y genera el feedback.</span>
          </span>
          <span className="btn btn-primary pointer-events-none">Ir a Feedback</span>
        </button>
      )}

      {/* Rejilla con filas: en MÓVIL el orden es identidad → contenido →
          extras (el coach llega a las pestañas sin scrollear toda la barra);
          en ESCRITORIO la columna izquierda tiene la ficha arriba y las
          tarjetas extra debajo, con el contenido a la derecha. */}
      <div className="mt-4 grid gap-4 lg:gap-6 lg:grid-cols-[300px_1fr] lg:grid-rows-[auto_1fr] lg:items-start">
        {/* 1) Identidad + info + Diario (arriba también en móvil) */}
        <aside className="min-w-0 space-y-4 lg:col-start-1 lg:row-start-1">
          <div className="card p-5">
            <div className="flex items-center gap-3">
              <Avatar name={client.full_name} size={48} />
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold text-zinc-100">{client.full_name}</h1>
                <p className="truncate text-xs text-zinc-500">{client.email}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatusBadge status={client.status} />
            </div>

            <dl className="mt-5 space-y-2.5 text-sm">
              <PlanRow client={client} onSaved={reload} />
              <BillingRow client={client} onSaved={reload} />
              <div className="flex items-center justify-between gap-2">
                <dt className="text-zinc-500">Pago</dt>
                <dd>
                  <span
                    className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
                    style={{
                      background: `color-mix(in srgb, ${client.payment_status === "paid" ? "#2E7D46" : "#C2453A"} 14%, transparent)`,
                      color: client.payment_status === "paid" ? "#2E7D46" : "#C2453A",
                    }}
                  >
                    {client.payment_status === "paid" ? "Pagado" : "Pago pendiente"}
                  </span>
                </dd>
              </div>
              <PhoneRow client={client} onSaved={reload} />
              <Row label="Edad" value={age ? `${age} años` : "—"} />
              {/* Filas HIPERMEDIA: pulsar el dato lleva al apartado que lo trata. */}
              <Row label="Objetivo" value={client.goal_type ? GOAL_LABEL[client.goal_type] : "—"}
                onGo={() => changeTab("planificacion")} />
              <Row label="Nivel" value={client.level ? LEVEL_LABEL[client.level] : "—"}
                onGo={() => changeTab("anamnesis")} />
              {hasTraining && (
                <Row label="Entreno" value={client.training_place ? PLACE_LABEL[client.training_place] : "—"}
                  onGo={() => changeTab("anamnesis")} />
              )}
              {/* Dieta = la generada con IA; vacía hasta que exista planificación */}
              <Row label="Dieta" value={planDiet ?? "—"}
                faint={planDiet == null ? "se llena al generar la planificación" : undefined}
                onGo={() => changeTab("planificacion")} />
              {/* Antigüedad del cliente: cuánto lleva en la asesoría, de un vistazo. */}
              <Row label="Cliente desde" value={formatDate(client.created_at)}
                faint={relativeDays(client.created_at)} />
              {client.payment_status === "paid" && client.paid_at && (
                <Row label="Último pago" value={formatDate(client.paid_at)} />
              )}
            </dl>
            {/* CUÁNTO ha pagado este cliente: el backend ya filtraba el feed
                por cliente y ninguna pantalla lo pedía, así que "¿le cobré la
                renovación de julio?" solo se respondía bajándose el CSV. */}
            <CobrosDelCliente clientId={client.id} onCambio={reload} />
          </div>

          {/* DIARIO DEL CLIENTE (su app del móvil): botón destacado y distinto. */}
          <button
            onClick={openPortal}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3.5 text-left text-white shadow-md transition-transform hover:brightness-110 active:scale-[0.98]"
            style={{ background: "linear-gradient(135deg, var(--brand-accent-2) 0%, #234B72 100%)" }}
          >
            <span className="relative shrink-0">
              <Smartphone size={26} />
              <ClipboardCheck
                size={14}
                className="absolute -bottom-1 -right-1.5 rounded-full p-0.5"
                style={{ background: "var(--brand-accent)", color: "white" }}
              />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">Diario del cliente</span>
              <span className="block text-xs opacity-75">abrir y copiar el enlace de su app</span>
            </span>
          </button>

          {/* ESCRIBIRLE POR WHATSAPP: media app le dice al coach "escríbele por
              WhatsApp" (alertas de anamnesis, cambios, videollamada, riesgo…) y
              no había ningún botón para hacerlo — tocaba buscar el número y
              abrir el chat a mano (auditoría de facilidad). */}
          <button
            onClick={() => {
              const digits = waPhone(client.phone);
              if (!digits) {
                toast.push("Este cliente no tiene teléfono guardado — añádelo arriba", "error");
                return;
              }
              openWhatsApp(digits, `Hola ${(client.full_name || "").split(" ")[0]}, `);
            }}
            className="flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left transition-transform active:scale-[0.98]"
            style={{ borderColor: "#25D366", color: "#128C4B", background: "color-mix(in srgb, #25D366 8%, transparent)" }}
          >
            <MessageCircle size={22} className="shrink-0" />
            <span className="min-w-0">
              <span className="block text-sm font-semibold" {...ancla("anamnesis.enviar")}>
                Escribirle por WhatsApp
              </span>
              <span className="block text-xs opacity-80">abre su chat con el saludo puesto</span>
            </span>
          </button>

          {/* ENLACE DE PAGO (Stripe): color diferenciado (verde), debajo del
              portal. Copia el enlace para mandárselo al cliente y que pague. */}
          <div {...ancla("resumen.pago")} className="space-y-3">
          {/* Manda lo que dice el BACKEND sobre ese enlace (payState): si no va a
              cobrar nada, no se ofrece como "enlace de pago". Su corazonada
              local queda de reserva mientras carga. */}
          {payUrl && (payState
            ? payState !== "pagado"
            : (client.payment_status !== "paid" || client.renewal_due)) && (
            <button
              onClick={() => {
                void copiarConAviso(payUrl, toast, client.payment_status === "paid"
                  ? "Enlace de renovación copiado — mándaselo al cliente"
                  : "Enlace de pago copiado — mándaselo al cliente");
              }}
              className="flex w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-left transition-transform active:scale-[0.98]"
              style={{ borderColor: "#2E7D46", color: "#2E7D46", background: "color-mix(in srgb, #2E7D46 7%, transparent)" }}
            >
              <CreditCard size={22} className="shrink-0" />
              <span className="min-w-0">
                <span className="block text-sm font-semibold">
                  {client.payment_status === "paid" ? "Enlace de renovación" : "Enlace de pago"}
                </span>
                <span className="block text-xs opacity-80">
                  {payNote ?? `copiar y enviar al cliente — ${client.payment_status === "paid" ? "renueva" : "cobra"} su plan ${billingLabel(client.billing_period).toLowerCase()}`}
                </span>
              </span>
            </button>
          )}
          {/* Pago por OTRA VÍA (bizum, transferencia, efectivo): sin este botón
              la ficha quedaba "Pago pendiente" para siempre, con la campana
              insistiendo y la carpeta "Falta pago" contaminada. */}
            <CobroManual client={client} onDone={reload} />
          </div>
          {/* Reactivar a un cliente INACTIVO: la transición existía en la
              máquina de estados pero no tenía ningún botón (auditoría del
              ciclo) — el cliente quedaba en un limbo sin alertas ni ciclo. */}
          {client.status === "inactive" && (
            <button
              {...ancla("resumen.estado")}
              onClick={async () => {
                if (!window.confirm(`¿Reactivar a ${client.full_name}? Volverá a recibir recordatorios y su ciclo de seguimiento continuará.`)) return;
                try {
                  await api.updateClient(client.id, { status: "active" } as any);
                  toast.push("Cliente reactivado");
                  reload();
                } catch (e: any) {
                  toast.push(e?.message ?? "No se pudo reactivar", "error");
                }
              }}
              className="w-full rounded-xl border border-emerald-600/40 bg-emerald-600/10 px-3 py-2 text-center text-xs font-semibold text-emerald-500 hover:bg-emerald-600/20"
            >
              Reactivar cliente
            </button>
          )}
        </aside>

        {/* 3) Extras: anamnesis + regenerar enlace (debajo del contenido en
            móvil; columna izquierda-abajo en escritorio) */}
        <aside className="order-last min-w-0 space-y-3 lg:order-none lg:col-start-1 lg:row-start-2">
          {/* Anamnesis: enviar enlace + subir PDF rellenado */}
          <ClientDocuments client={client} onUploaded={reload}
            onGoAnamnesis={() => changeTab("anamnesis")}
            portalUrl={portalUrl} anamnesisUrl={anamnesisUrl} />
          <button
            onClick={() => setConfirmRegen(true)}
            className="w-full text-center text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
          >
            Regenerar enlace del portal (el actual dejará de funcionar)
          </button>
          {/* Zona peligrosa: borrado total del cliente. Botón claramente en ROJO
              (borde + texto + fondo tenue) y separado del resto; el modal exige
              teclear el nombre completo antes de confirmar, así que verse rojo no
              lo hace peligroso de pulsar. */}
          <button
            onClick={() => setConfirmDelete(true)}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border py-2.5 text-xs font-semibold text-white transition-colors"
            style={{ background: "#C2453A", borderColor: "#C2453A" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#A93A30")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#C2453A")}
          >
            <Trash2 size={13} /> Borrar cliente
          </button>
        </aside>

        {/* 2) CONTENIDO con tabs (a la derecha, ocupa ambas filas en desktop) */}
        <div className="min-w-0 lg:col-start-2 lg:row-start-1 lg:row-span-2">
          {/* Barra de pestañas PEGAJOSA: al hacer scroll de un plan largo, la
              navegación entre secciones sigue siempre accesible. */}
          <div className="profile-tabs mb-5 flex gap-1 border-b" style={{ borderColor: "var(--line)", position: "sticky", top: 0, zIndex: 10, background: "var(--bg)" }}>
            {(["resumen", "anamnesis", "planificacion", "seguimiento", "feedback", "historial"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => changeTab(t)}
                className="tab-btn relative px-4 py-2.5 text-sm font-medium capitalize transition-colors"
                style={{ color: tab === t ? "#26211A" : "var(--text-faint)" }}
              >
                {t === "resumen" ? "Resumen" : t === "anamnesis" ? "Anamnesis" : t === "planificacion" ? "Planificación" : t === "seguimiento" ? "Seguimiento" : t === "feedback" ? "Feedback" : "Historial"}
                {tab === t && (
                  <span
                    className="absolute inset-x-2 -bottom-px h-0.5 rounded-full"
                    style={{ background: "var(--brand-accent)" }}
                  />
                )}
              </button>
            ))}
          </div>

          {/* key=cliente+tab: el panel se re-monta al cambiar de pestaña (su
              micro-animación) Y al cambiar de CLIENTE — sin el id en la key,
              el borrador a medias de la anamnesis del cliente A sobrevivía al
              salto al perfil de B y "Guardar" volcaba los datos de A sobre la
              ficha de B (auditoría crítica: corrupción de datos entre fichas). */}
          <div key={`${client.id}-${tab}`} className="tab-panel">
            {tab === "resumen" && <ClientSummaryTab client={client} />}
            {tab === "anamnesis" && <ClientAnamnesisTab client={client} onSaved={reload} onDirtyChange={setAnamnesisDirty} />}
            {tab === "planificacion" && <ClientPlanPanel client={client} onClientChanged={reload} onEditingChange={setPlanEditing} onGoTab={(t) => changeTab(t as Tab)} />}
            {tab === "seguimiento" && <ClientTrackingTab client={client} />}
            {tab === "feedback" && <ClientFeedbackTab client={client} onClientChanged={reload} onGoPlan={() => changeTab("planificacion")} />}
            {tab === "historial" && <ClientHistoryTab client={client} />}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmRegen}
        title="Regenerar enlace del portal"
        body="El enlace actual dejará de funcionar de inmediato. Tendrás que enviar el nuevo al cliente."
        confirmLabel="Regenerar"
        onConfirm={regenerate}
        onCancel={() => setConfirmRegen(false)}
      />

      <ConfirmDialog
        open={confirmDelete}
        title="Borrar cliente"
        destructive
        requireText={client.full_name}
        body={
          <>
            Se borrará <b>para siempre</b> todo lo de <b>{client.full_name}</b>:
            ficha, anamnesis, planificaciones, seguimiento, fotos y feedbacks.
            <b> No se puede deshacer.</b>
            <br />
            <br />
            Para confirmar, escribe el nombre completo del cliente:
          </>
        }
        confirmLabel={deleting ? "Borrando…" : "Borrar definitivamente"}
        onConfirm={deleteClient}
        onCancel={() => !deleting && setConfirmDelete(false)}
      />
    </div>
  );
}

/** Plan/paquete del cliente: badge + desplegable para cambiarlo (upgrade/downgrade).
 *  Cambiarlo adapta toda la app (portal, planificación, envíos) a ese plan. */
function PlanRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const info = pkg(client.package_tier);

  async function change(next: string) {
    if (busy || next === client.package_tier) return;
    // Un select suelto que guardaba al primer cambio de valor: pasar de Full a
    // Nutri deja al cliente sin entrenamiento en su portal y en su PDF, sin
    // avisar a nadie y sin forma de deshacer. Todo lo demás peligroso de la
    // app pregunta antes; esto también. Un cambio que AÑADE servicio sigue
    // siendo directo.
    const antes = pkg(client.package_tier);
    const ahora = pkg(next);
    const pierdeEntreno = antes.hasTraining && !ahora.hasTraining;
    const pierdeDieta = antes.hasNutrition && !ahora.hasNutrition;
    if (pierdeEntreno || pierdeDieta) {
      const que = pierdeEntreno && pierdeDieta
        ? "su dieta y su entrenamiento"
        : pierdeEntreno ? "su entrenamiento" : "su dieta";
      if (!window.confirm(
        `${client.full_name} pasa a ${PACKAGES[next as keyof typeof PACKAGES].label}: `
        + `dejará de ver ${que} en su portal y en su PDF. ¿Seguro?`)) return;
    }
    setBusy(true);
    try {
      await api.updateClient(client.id, { package_tier: next as ClientOut["package_tier"] });
      toast.push(`Plan cambiado a ${PACKAGES[next as keyof typeof PACKAGES].label}`);
      onSaved();
    } catch {
      toast.push("No se pudo cambiar el plan", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Plan</dt>
      <dd className="flex items-center gap-1.5">
        <span
          className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{ background: `color-mix(in srgb, ${info.color} 14%, transparent)`, color: info.color }}
        >
          {info.label}
        </span>
        <select
          aria-label="Cambiar plan del cliente"
          disabled={busy}
          value={client.package_tier}
          onChange={(e) => change(e.target.value)}
          className="input h-7 w-auto px-1.5 py-0 text-xs"
        >
          {PACKAGE_ORDER.map((t) => (
            <option key={t} value={t}>{PACKAGES[t].short}</option>
          ))}
        </select>
      </dd>
    </div>
  );
}

/** Duración contratada (mensual/trimestral/semestral): decide el precio de
 *  Stripe que abre el enlace de pago del cliente. Cambiarla aquí y reenviar el
 *  enlace basta para cobrar la duración nueva. */
function BillingRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);

  async function change(next: string) {
    if (busy || next === client.billing_period) return;
    // Cambia lo que COBRARÁ su enlace de pago: no puede pasar por un roce en
    // el select (en móvil son lo primero bajo el nombre del cliente).
    if (!window.confirm(
      `${client.full_name} pasa a ${billingLabel(next)}: su enlace de pago `
      + "cobrará ese importe a partir de ahora. ¿Seguro?")) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, { billing_period: next as ClientOut["billing_period"] });
      toast.push(`Duración cambiada a ${billingLabel(next)} — su enlace de pago ya cobra ese precio`);
      onSaved();
    } catch {
      toast.push("No se pudo cambiar la duración", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Duración</dt>
      <dd>
        <select
          aria-label="Cambiar duración del plan del cliente"
          disabled={busy}
          value={client.billing_period}
          onChange={(e) => change(e.target.value)}
          className="input h-7 w-auto px-1.5 py-0 text-xs"
        >
          {BILLING_PERIODS.map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
          {/* La oferta se muestra y se puede (re)aplicar SOLO en plan Full:
              sin esta opción, un cliente de la oferta salía con el select en
              blanco y cambiarlo era un billete de ida sin vuelta. */}
          {pkg(client.package_tier).tier === "full" && (
            <>
              <option value="oferta">Oferta · 1 € + 120 € + 120 € (3 meses)</option>
              <option value="oferta2">Oferta · 2 pagos de 120,50 €</option>
            </>
          )}
        </select>
      </dd>
    </div>
  );
}

/** Teléfono editable en línea: imprescindible para los envíos por WhatsApp
 *  (feedback y plan). Lápiz → escribir → Enter o ✓ para guardar. */
function PhoneRow({ client, onSaved }: { client: ClientOut; onSaved: () => void }) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(client.phone ?? "");
  const [busy, setBusy] = useState(false);

  useEffect(() => setValue(client.phone ?? ""), [client.phone]);

  async function save() {
    if (busy) return;
    setBusy(true);
    try {
      await api.updateClient(client.id, { phone: value.trim() || null });
      toast.push("Teléfono guardado");
      setEditing(false);
      onSaved();
    } catch {
      toast.push("No se pudo guardar el teléfono", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-zinc-500">Teléfono</dt>
      {editing ? (
        <dd className="flex items-center gap-1.5">
          <input
            autoFocus
            type="tel"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") save();
              if (e.key === "Escape") setEditing(false);
            }}
            placeholder="612 345 678"
            className="input w-36 px-2 py-1 text-sm"
          />
          <button onClick={save} disabled={busy} aria-label="Guardar teléfono" className="p-1 text-zinc-500 hover:text-zinc-200">
            <Check size={16} />
          </button>
        </dd>
      ) : (
        <dd className="flex items-center gap-1.5 font-medium text-zinc-200">
          {client.phone || <span className="font-normal text-zinc-500">añádelo para WhatsApp</span>}
          <button onClick={() => setEditing(true)} aria-label="Editar teléfono" className="p-1 text-zinc-500 hover:text-zinc-200">
            <Pencil size={13} />
          </button>
        </dd>
      )}
    </div>
  );
}

function Row({ label, value, faint, onGo }: {
  label: string; value: string; faint?: string;
  /** Hipermedia: pulsar la fila navega al apartado que trata ese dato. */
  onGo?: () => void;
}) {
  const body = (
    <>
      <dt className="text-zinc-500">{label}</dt>
      <dd className="flex items-center justify-end gap-1 text-right font-medium text-zinc-200">
        <span>
          {value}
          {faint && <span className="block text-[11px] font-normal text-zinc-500">{faint}</span>}
        </span>
        {onGo && (
          <ChevronRight size={13} className="shrink-0 text-zinc-600 transition-colors group-hover:text-[var(--brand-accent)]" />
        )}
      </dd>
    </>
  );
  if (!onGo) return <div className="flex items-center justify-between gap-2">{body}</div>;
  return (
    <div
      role="link"
      tabIndex={0}
      onClick={onGo}
      onKeyDown={(e) => e.key === "Enter" && onGo()}
      className="group -mx-1.5 flex cursor-pointer items-center justify-between gap-2 rounded-lg px-1.5 py-0.5 transition-colors hover:bg-[color-mix(in_srgb,var(--brand-accent)_7%,transparent)]"
      title={`Ir a ${label.toLowerCase()}`}
    >
      {body}
    </div>
  );
}

/** Cobro FUERA de Stripe (efectivo, transferencia, Bizum).
 *
 *  Pide el IMPORTE además de marcar la ficha: sin la cifra, el libro de caja
 *  solo contaba la pasarela y el total del mes mentía en cuanto el cliente
 *  pagaba por otra vía. La fecha por defecto es hoy, pero se puede corregir:
 *  un cobro apuntado con retraso cuenta en el mes en que se cobró.
 */
/** Fecha de HOY en horario LOCAL (YYYY-MM-DD). `toISOString()` da la de UTC:
 *  en España, de madrugada, apuntaba al día —y a veces al mes— anterior. */
function hoyLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function CobrosDelCliente({ clientId, onCambio }: { clientId: number; onCambio: () => void }) {
  const toast = useToast();
  const [pagos, setPagos] = useState<PaymentsListOut["items"] | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [borrando, setBorrando] = useState<number | null>(null);

  const cargar = useCallback(() => {
    api.listPayments({ client_id: clientId, limit: 20 })
      .then((r) => setPagos(r.items))
      .catch(() => setPagos([]));
  }, [clientId]);
  useEffect(cargar, [cargar]);

  if (!pagos || pagos.length === 0) return null;
  // Los cobros suman y las devoluciones restan: el total es lo que ha entrado.
  const total = pagos.reduce(
    (a, p) => a + (p.status === "refunded" ? -p.amount_cents : p.status === "paid" ? p.amount_cents : 0), 0);
  const eur = (c: number) => (c / 100).toLocaleString("es-ES", { minimumFractionDigits: 2 });

  async function borrar(id: number) {
    if (!window.confirm("¿Borrar este cobro anotado a mano? El total del mes se recalcula.")) return;
    setBorrando(id);
    try {
      await api.borrarCobro(id);
      toast.push("Cobro borrado");
      cargar();
      onCambio();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo borrar", "error");
    } finally {
      setBorrando(null);
    }
  }

  return (
    <details className="mt-2" onToggle={(e) => setAbierto((e.target as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
        Cobros ({pagos.length}) · {eur(total)} €
      </summary>
      {abierto && (
        <ul className="mt-2 space-y-1">
          {pagos.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 text-xs">
              <span className="min-w-0 flex-1 truncate text-zinc-400" title={p.description ?? ""}>
                {new Date(p.paid_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short" })}
                {" · "}{p.description || p.kind}
              </span>
              <span className="tabular-nums font-medium"
                style={{ color: p.status === "refunded" ? "#C2453A" : p.status === "paid" ? "var(--brand-accent)" : "var(--text-faint)" }}>
                {p.status === "refunded" ? "−" : ""}{eur(p.amount_cents)} €
              </span>
              {p.kind === "manual" && (
                <button onClick={() => borrar(p.id)} disabled={borrando === p.id}
                  className="shrink-0 text-zinc-600 hover:text-red-400" title="Borrar este cobro a mano">
                  <Trash2 size={12} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}


function CobroManual({ client, onDone }: { client: ClientOut; onDone: () => void }) {
  const toast = useToast();
  const [abierto, setAbierto] = useState(false);
  const [importe, setImporte] = useState("");
  const [metodo, setMetodo] = useState<"efectivo" | "transferencia" | "bizum" | "otro">("transferencia");
  const [fecha, setFecha] = useState(hoyLocal);
  // El 409 de duplicado pide "añádele una nota que los distinga" y el
  // formulario no tenía dónde escribirla: la instrucción era imposible de
  // seguir (el campo ya viajaba en el schema).
  const [nota, setNota] = useState("");
  const [guardando, setGuardando] = useState(false);

  // Coma o punto: en España se teclea "129,50".
  const eur = Number((importe || "").replace(",", "."));
  const valido = Number.isFinite(eur) && eur > 0;

  async function registrar() {
    if (!valido || guardando) return;
    setGuardando(true);
    try {
      await api.registrarCobroManual({
        client_id: client.id, amount_eur: eur, method: metodo, paid_on: fecha,
        note: nota.trim() || undefined,
      });
      toast.push(`Cobro de ${eur.toLocaleString("es-ES", { minimumFractionDigits: 2 })} € anotado`);
      setAbierto(false);
      setImporte("");
      setNota("");
      onDone();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo anotar el cobro", "error");
    } finally {
      setGuardando(false);
    }
  }

  if (!abierto) {
    return (
      <button
        onClick={() => setAbierto(true)}
        className="w-full text-center text-xs text-zinc-500 underline-offset-2 hover:text-zinc-300 hover:underline"
      >
        {client.payment_status === "paid"
          ? "Anotar otro cobro (renovación, extra…)"
          : "¿Te pagó por otra vía? Anotar el cobro"}
      </button>
    );
  }

  return (
    <div className="rounded-xl border p-3" style={{ borderColor: "var(--line-strong)" }}>
      <p className="mb-2 text-xs font-semibold text-zinc-200">Cobro fuera de Stripe</p>
      <div className="flex gap-2">
        <label className="flex-1">
          <span className="mb-1 block text-[11px] text-zinc-500">Importe (€)</span>
          <input
            type="text" inputMode="decimal" autoFocus value={importe}
            onChange={(e) => setImporte(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") registrar(); }}
            placeholder="129,00" className="input w-full"
          />
        </label>
        <label className="flex-1">
          <span className="mb-1 block text-[11px] text-zinc-500">Cómo</span>
          <select value={metodo} onChange={(e) => setMetodo(e.target.value as typeof metodo)} className="input w-full">
            <option value="transferencia">Transferencia</option>
            <option value="efectivo">Efectivo</option>
            <option value="bizum">Bizum</option>
            <option value="otro">Otro</option>
          </select>
        </label>
      </div>
      <label className="mt-2 block">
        <span className="mb-1 block text-[11px] text-zinc-500">Fecha del cobro</span>
        <input type="date" value={fecha} max={hoyLocal()}
          onChange={(e) => setFecha(e.target.value)} className="input w-full" />
      </label>
      <label className="mt-2 block">
        <span className="mb-1 block text-[11px] text-zinc-500">Nota (opcional)</span>
        <input type="text" value={nota} maxLength={120}
          onChange={(e) => setNota(e.target.value)}
          placeholder="Ej.: segunda mensualidad" className="input w-full" />
      </label>
      <div className="mt-3 flex justify-end gap-2">
        <button onClick={() => setAbierto(false)} className="btn btn-ghost !py-1.5 text-xs">Cancelar</button>
        <button onClick={registrar} disabled={!valido || guardando} className="btn btn-primary !py-1.5 text-xs">
          {guardando ? "Anotando…" : "Anotar cobro"}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-zinc-500">Suma en el total del mes, junto a los cobros de Stripe.</p>
    </div>
  );
}
