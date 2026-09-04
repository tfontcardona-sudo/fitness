import { useEffect, useRef, useState } from "react";
import { copiarConAviso } from "../lib/clipboard";
import { CheckCircle2, Download, FileText, MessageCircle, Send, Sparkles, Trash2, Upload } from "lucide-react";
import { api, getToken } from "../lib/api";
import type { AttachmentSummary } from "../lib/api";
import { ACEPTA_DOCUMENTOS , resumenDudas } from "../lib/documentos";
import { Spinner, useToast } from "./ui";
import { anamnesisReminderMessage, openWhatsApp, portalAccessMessage, waPhone } from "../lib/whatsapp";
import type { ClientOut } from "../types";

interface DocItem {
  name: string;
  kind?: string;
  format?: string;
  size_kb: number;
  uploaded_at: number;
}

/** Etiqueta del badge de formato: lo que dice el backend (por la magia del
 *  archivo) o, si falta, la extensión del nombre. */
function formatoDe(d: DocItem): string {
  const f = (d.format ?? (d.name.includes(".") ? d.name.split(".").pop() : "") ?? "").trim();
  return f ? f.toUpperCase() : "DOC";
}

/** Nombre base de un fichero (los resúmenes pueden venir con ruta relativa). */
const base = (p: string) => p.split("/").pop() ?? p;

function fechaCorta(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-ES");
}

/**
 * Anamnesis y adjuntos del cliente. La anamnesis se sube en CUALQUIER formato
 * (PDF, Word, fotos del cuestionario, Excel): la IA la lee y rellena la ficha.
 * Los adjuntos (analítica, informes) también se leen y su contenido entra en
 * las notas de la ficha. Luego el coach revisa en la pestaña "Anamnesis".
 */
export function ClientDocuments({ client, onUploaded, onGoAnamnesis, portalUrl, anamnesisUrl }: {
  client: ClientOut;
  onUploaded?: () => void;
  /** Llevar a la pestaña Anamnesis: el aviso de "revisa los datos" no dice
   *  dónde están, lleva hasta ellos. */
  onGoAnamnesis?: () => void;
  portalUrl?: string | null;
  anamnesisUrl?: string | null;
}) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const adjRef = useRef<HTMLInputElement>(null);
  const [docs, setDocs] = useState<DocItem[] | null>(null);
  // Resúmenes de los adjuntos leídos con IA, por nombre base del fichero.
  const [resumenes, setResumenes] = useState<Record<string, AttachmentSummary>>({});
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [releyendo, setReleyendo] = useState<string | null>(null);
  const [borrando, setBorrando] = useState<string | null>(null);

  function load() {
    api.listClientDocuments(client.id).then(setDocs).catch(() => setDocs([]));
    // Los resúmenes viajan aparte: si fallan, la lista de documentos se enseña
    // igual (con "Sin leer" y el botón de leer).
    api.listClientAttachments(client.id)
      .then((lista) => {
        const m: Record<string, AttachmentSummary> = {};
        for (const a of lista) m[base(a.file)] = a;
        setResumenes(m);
      })
      .catch(() => {});
  }

  const resumenDe = (name: string): AttachmentSummary | undefined => resumenes[base(name)];

  // El CUESTIONARIO y los ADJUNTOS (analítica, informes) son cosas distintas:
  // con todo en un montón, subir una analítica plegaba la tarjeta con el check
  // "subida" y daba la anamnesis por recibida, mientras la campana seguía
  // diciendo que faltaba.
  const anamnesis = (docs ?? []).filter((d) => d.kind !== "adjunto");
  const adjuntos = (docs ?? []).filter((d) => d.kind === "adjunto");
  useEffect(load, [client.id]);

  function downloadTemplate() {
    // El endpoint exige JWT; descargamos con fetch→blob para adjuntar el header.
    fetch(api.anamnesisTemplateUrl(), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "anamnesis.pdf";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.push("No se pudo descargar la plantilla", "error"));
  }

  /** Primera línea útil de un adjunto leído (resumen o, si no, alerta). */
  const primeraLinea = (a: AttachmentSummary | null | undefined): string | null =>
    a?.summary?.[0] ?? a?.alerts?.[0] ?? null;

  // Sube la ANAMNESIS en cualquier formato. Varios ficheros (fotos de cada
  // página) van en la misma petición y el backend los trata como UN documento.
  // La validación del formato la hace el backend por la magia del archivo.
  async function upload(files: File[]) {
    if (busy || !files.length) return;
    setBusy(true);
    try {
      const res = await api.uploadClientDocument(client.id, files.length === 1 ? files[0] : files);
      const accion = onGoAnamnesis ? { label: "Revisar", onClick: onGoAnamnesis } : undefined;
      if (res.redirected_to === "adjunto") {
        // La IA vio una analítica/informe/plan: quedó como ADJUNTO y la
        // anamnesis no se tocó. Se dice tal cual lo explica el backend.
        toast.push(
          res.document_warning
            ?? "El documento parece un informe o analítica: se ha guardado como adjunto y la anamnesis no se ha tocado",
          "error",
        );
      } else if (res.verification?.needs_review) {
        // El motivo, por partes (desajustes / confianza baja en QUÉ campos /
        // datos echados en falta): «no coincide en 0 datos» no orienta a nadie.
        toast.push(`Leída con dudas: ${resumenDudas(res.verification)} — revísalo`, "error", accion);
      } else if (res.document_warning) {
        toast.push(res.document_warning, "error");
      } else if (res.read_ok) {
        toast.push("Anamnesis leída · revísala", "ok", accion);
      } else {
        toast.push("Anamnesis subida · falta leerla", "ok",
                   onGoAnamnesis ? { label: "Leer con IA", onClick: onGoAnamnesis } : undefined);
      }
      // Acceso al portal: se envía automáticamente la primera vez que se
      // registra la anamnesis. Informamos del resultado en todos los casos.
      notifyPortalAccess(res.portal_access);
      onUploaded?.();
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo subir el documento", "error");
    } finally {
      setBusy(false);
    }
  }

  // ADJUNTO (analítica, informe médico…): documento ADICIONAL. No sustituye la
  // anamnesis — antes la única vía de subida BORRABA la anamnesis y leía el
  // informe de sangre como si fuera el cuestionario. Ahora se lee con IA y su
  // contenido entra en las notas de la ficha.
  async function uploadAdjunto(files: File[]) {
    if (busy || !files.length) return;
    setBusy(true);
    try {
      const res = await api.uploadClientDocument(
        client.id, files.length === 1 ? files[0] : files, "adjunto");
      if (res.read_ok) {
        const linea = primeraLinea(res.attachment);
        toast.push(linea ? `Adjunto leído: ${linea}` : "Adjunto leído");
        onUploaded?.(); // su bloque ya está en las notas de la ficha
      } else {
        const nombre = res.name;
        toast.push(
          `Adjunto guardado; la lectura falló (${res.read_error ?? "sin detalle"})`,
          "error", { label: "Leer", onClick: () => { void releer(nombre); } });
      }
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo subir el adjunto", "error");
    } finally {
      setBusy(false);
    }
  }

  /** Relee un documento con IA (gasta créditos). Para un adjunto refresca su
   *  resumen y su bloque en la ficha. */
  async function releer(name: string) {
    if (releyendo) return;
    setReleyendo(name);
    try {
      const r = await api.readClientDocument(client.id, name);
      if (r.read_ok) {
        const linea = primeraLinea(r.attachment);
        toast.push(linea ? `Adjunto leído: ${linea}` : "Documento leído");
        onUploaded?.();
      } else {
        toast.push(`La lectura falló (${r.read_error ?? "sin detalle"})`, "error");
      }
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo leer el documento", "error");
    } finally {
      setReleyendo(null);
    }
  }

  /** Borra un adjunto. Si estaba leído, el backend retira su bloque de las
   *  notas de la ficha: se avisa antes y se refresca el perfil después. */
  async function borrar(d: DocItem) {
    if (borrando) return;
    const leido = Boolean(resumenDe(d.name));
    const pregunta = leido
      ? `¿Borrar «${d.name}»? Estaba leído: su bloque se retirará de las notas de la ficha.`
      : `¿Borrar «${d.name}»?`;
    if (!window.confirm(pregunta)) return;
    setBorrando(d.name);
    try {
      await api.deleteClientDocument(client.id, d.name);
      toast.push(leido ? "Adjunto borrado · su bloque se ha retirado de la ficha" : "Adjunto borrado");
      if (leido) onUploaded?.();
      load();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo borrar el adjunto", "error");
    } finally {
      setBorrando(null);
    }
  }

  // Traduce el estado del envío del acceso al portal en un aviso claro para el
  // coach. Cubre todos los casos que puede devolver el backend.
  function notifyPortalAccess(status: string | null) {
    switch (status) {
      case "sent":
        toast.push("Acceso al portal enviado al cliente por email.");
        break;
      case "disabled":
        toast.push(
          "Acceso generado, pero el envío de correos está desactivado. Usa 'Reenviar acceso' para ver la contraseña.",
          "error",
        );
        break;
      case "failed":
      case "error":
        toast.push(
          "El acceso se generó pero el email no salió. Revisa la configuración de correo y usa 'Reenviar acceso'.",
          "error",
        );
        break;
      case "no_email":
        toast.push(
          "El cliente no tiene email en su ficha; añádelo para poder enviarle el acceso al portal.",
          "error",
        );
        break;
      default:
        // null = ya se había enviado antes; no hace falta avisar.
        break;
    }
  }

  async function resendAccess() {
    if (sending) return;
    setSending(true);
    try {
      const res = await api.sendPortalAccess(client.id);
      if (res.status === "sent") {
        toast.push("Acceso reenviado al cliente por email.");
      } else if (res.status === "no_email") {
        toast.push("El cliente no tiene email en su ficha; añádelo para enviarle el acceso.", "error");
      } else if (res.status === "disabled" && res.password) {
        toast.push(`Envío de correos desactivado. Contraseña del cliente: ${res.password}`, "error");
      } else if (res.status === "failed" && res.password) {
        toast.push(`El email no salió (revisa la configuración de correo). Contraseña del cliente: ${res.password}`, "error");
      } else if (res.password) {
        toast.push(`Acceso generado. Contraseña: ${res.password}`);
      } else {
        toast.push("No se pudo enviar el acceso", "error");
      }
      onUploaded?.();
    } catch (e: any) {
      toast.push(e?.message ?? "No se pudo enviar el acceso", "error");
    } finally {
      setSending(false);
    }
  }

  // Envía el acceso al portal por WhatsApp (alternativa/añadido al correo).
  // Necesita el teléfono del cliente y el enlace del portal ya cargado.
  function sendPortalWhatsApp() {
    const digits = waPhone(client.phone);
    if (!digits) {
      toast.push("Añade el teléfono del cliente en su ficha para enviarlo por WhatsApp", "error");
      return;
    }
    if (!portalUrl) {
      toast.push("El enlace del portal aún se está cargando; inténtalo en un segundo", "error");
      return;
    }
    openWhatsApp(digits, portalAccessMessage(client.full_name, portalUrl));
    toast.push("WhatsApp abierto con el acceso al portal — dale a enviar");
  }

  // REENVIAR el cuestionario: es la petición más repetida del panel ("recuérdale
  // que suba la anamnesis") y no existía en ninguna pantalla — había que
  // reconstruir la URL a mano (auditoría de calidad).
  function resendAnamnesis() {
    const url = anamnesisUrl ?? (portalUrl ? portalUrl.replace("/p/", "/anamnesis/") : null);
    if (!url) {
      toast.push("El enlace del cuestionario aún se está cargando; inténtalo en un segundo", "error");
      return;
    }
    const digits = waPhone(client.phone);
    if (digits) {
      openWhatsApp(digits, anamnesisReminderMessage(client.full_name, url));
      toast.push("WhatsApp abierto con su cuestionario — dale a enviar");
      return;
    }
    void copiarConAviso(url, toast,
      "Enlace del cuestionario copiado (el cliente no tiene teléfono en su ficha)");
  }

  function openDoc(name: string) {
    // El endpoint exige JWT; abrimos con fetch→blob para adjuntar el header.
    // El backend sirve el MIME real, así que el navegador abre PDF y fotos en
    // la pestaña y descarga lo que no sabe pintar (Word, Excel).
    fetch(api.clientDocumentUrl(client.id, name), {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Error ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
        setTimeout(() => URL.revokeObjectURL(url), 60000);
      })
      .catch(() => toast.push("No se pudo abrir el documento", "error"));
  }

  /** Lo que se ve bajo un ADJUNTO: su resumen (máx. 3 líneas), las alertas en
   *  ámbar, los valores fuera de rango como chips y los botones de releer y
   *  borrar. Sin resumen, "Sin leer" con el botón de leer. */
  function detalleAdjunto(d: DocItem) {
    const r = resumenDe(d.name);
    const fuera = r?.out_of_range ?? [];
    const cabecera = r
      ? [r.document_kind, r.title, fechaCorta(r.document_date)].filter(Boolean).join(" · ")
      : "";
    return (
      <div className="mt-2 space-y-1.5 pl-6">
        {r ? (
          <>
            {cabecera && <p className="text-xs text-zinc-400">{cabecera}</p>}
            {r.summary.slice(0, 3).map((s, i) => (
              <p key={i} className="text-xs text-zinc-300">{s}</p>
            ))}
            {r.alerts.map((a, i) => (
              <p key={i} className="text-xs font-medium" style={{ color: "#9A6B15" }}>⚠ {a}</p>
            ))}
            {fuera.length > 0 && (
              <div className="flex flex-wrap items-center gap-1">
                {fuera.slice(0, 6).map((v) => (
                  <span key={v} className="rounded-full px-2 py-0.5 text-[11px]"
                    style={{ background: "color-mix(in srgb, #9A6B15 14%, transparent)", color: "#9A6B15" }}>
                    {v}
                  </span>
                ))}
                {fuera.length > 6 && (
                  <span className="text-[11px] text-zinc-500">+{fuera.length - 6} más</span>
                )}
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-zinc-500">Sin leer</p>
        )}
        <div className="flex flex-wrap gap-1.5">
          <button onClick={() => void releer(d.name)} disabled={releyendo !== null || busy}
            className="btn btn-ghost !px-2 !py-1 text-xs"
            title={r ? "Volver a leerlo con IA (gasta créditos)" : "Leerlo con IA para que entre en la ficha"}>
            {releyendo === d.name ? <Spinner className="!h-3 !w-3" /> : <Sparkles size={12} />} Leer con IA
          </button>
          <button onClick={() => void borrar(d)} disabled={borrando !== null}
            className="btn btn-ghost !px-2 !py-1 text-xs text-zinc-400">
            {borrando === d.name ? <Spinner className="!h-3 !w-3" /> : <Trash2 size={12} />} Borrar
          </button>
        </div>
      </div>
    );
  }

  return (
    // DESPLEGABLE: abierto solo mientras falte la anamnesis (hay que actuar);
    // una vez subida queda plegado y el check lo resume de un vistazo.
    <details className="card p-5" open={!docs || anamnesis.length === 0}>
      <summary className="flex cursor-pointer items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-200">Anamnesis</h3>
        {docs && anamnesis.length > 0 && (
          <span
            className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
            style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)", color: "var(--brand-accent)" }}
          >
            <CheckCircle2 size={13} /> subida
          </span>
        )}
      </summary>
      <p className="mt-1 mb-4 text-xs text-zinc-500">
        Sube la anamnesis en cualquier formato (PDF, Word, fotos del cuestionario,
        Excel); la IA la lee y rellena la ficha. Los adjuntos (analítica, informes)
        también se leen y entran en la ficha.
      </p>

      <button onClick={downloadTemplate} className="btn btn-ghost mb-2 w-full justify-start">
        <Download size={15} className="text-zinc-500" /> Descargar anamnesis (PDF)
      </button>

      {/* REENVIAR el cuestionario: es la petición más repetida del panel
          ("reenvíale el enlace si hace falta") y no existía en ninguna
          pantalla — tocaba reconstruir la URL a mano (auditoría). */}
      <button onClick={resendAnamnesis} className="btn btn-ghost mb-3 w-full justify-start">
        <MessageCircle size={15} style={{ color: "#25D366" }} /> Reenviarle su cuestionario
      </button>

      {/* Zona de subida (arrastrar o clic). Admite varios ficheros: las fotos
          de cada página del cuestionario viajan juntas como UN documento. */}
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const fs = Array.from(e.dataTransfer.files ?? []);
          if (fs.length) void upload(fs);
        }}
        className="flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed py-6 text-center transition-colors"
        style={{
          borderColor: dragOver ? "var(--brand-accent)" : "var(--line-strong)",
          background: dragOver ? "color-mix(in srgb, var(--brand-accent) 6%, transparent)" : "transparent",
        }}
      >
        <Upload size={18} className="text-zinc-500" />
        <p className="mt-2 text-xs text-zinc-400">
          {busy
            ? "Subiendo y leyendo con IA…"
            : anamnesis.length > 0
            ? "Arrastra otro documento para reemplazar"
            : "Arrastra la anamnesis aquí (PDF, Word, fotos o Excel) o haz clic"}
        </p>
      </div>
      <input
        ref={fileRef}
        type="file"
        accept={ACEPTA_DOCUMENTOS}
        multiple
        hidden
        onChange={(e) => {
          const fs = Array.from(e.target.files ?? []);
          if (fs.length) void upload(fs);
          e.target.value = "";
        }}
      />

      {/* Adjuntos: la analítica que el propio cuestionario pide, informes…
          Va aparte para que NUNCA sustituya a la anamnesis. */}
      <button onClick={() => adjRef.current?.click()} disabled={busy}
        className="btn btn-ghost mt-2 w-full justify-start text-xs">
        <FileText size={14} className="text-zinc-500" /> Subir adjunto (analítica, informes…)
      </button>
      <input
        ref={adjRef}
        type="file"
        accept={ACEPTA_DOCUMENTOS}
        multiple
        hidden
        onChange={(e) => {
          const fs = Array.from(e.target.files ?? []);
          if (fs.length) void uploadAdjunto(fs);
          e.target.value = "";
        }}
      />

      {/* Lista de documentos, con los ADJUNTOS en su propio grupo */}
      {(() => {
        const grupos: [string, DocItem[]][] = [
          ["", anamnesis],
          ["Adjuntos (analítica, informes)", adjuntos],
        ];
        return grupos.map(([titulo, lista]) => (
          lista.length > 0 && (
            <div key={titulo || "anamnesis"}>
              {titulo && (
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  {titulo}
                </p>
              )}
              <ul className={titulo ? "mt-1.5 space-y-1.5" : "mt-4 space-y-1.5"}>
                {lista.map((d) => (
                  <li key={d.name} className="rounded-lg px-3 py-2.5 hover:bg-[var(--surface-raised)]">
                    <div className="flex items-center gap-2.5">
                      <FileText size={15} className="shrink-0" style={{ color: "var(--brand-accent)" }} />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-zinc-200" title={d.name}>{d.name}</span>
                        <span className="flex items-center gap-1.5 text-xs text-zinc-500">
                          <span
                            className="rounded px-1.5 py-px text-[10px] font-semibold tracking-wide"
                            style={{ background: "color-mix(in srgb, var(--brand-accent) 12%, transparent)", color: "var(--brand-accent)" }}
                          >
                            {formatoDe(d)}
                          </span>
                          {d.size_kb} KB
                        </span>
                      </span>
                      <button onClick={() => openDoc(d.name)}
                        className="btn btn-ghost shrink-0 !px-2 !py-1 text-xs" title="Abrir el documento">
                        Ver
                      </button>
                    </div>
                    {d.kind === "adjunto" && detalleAdjunto(d)}
                  </li>
                ))}
              </ul>
            </div>
          )
        ));
      })()}

      {/* Acceso al portal del cliente (usuario = su email + contraseña por email).
          Se envía solo al subir la anamnesis; aquí el coach puede reenviarlo por
          email o mandar el enlace del portal por WhatsApp. */}
      <div className="mt-4 border-t pt-3" style={{ borderColor: "var(--line)" }}>
        <span className="text-xs text-zinc-500">
          {client.portal_access_sent_at
            ? `Acceso enviado el ${new Date(client.portal_access_sent_at).toLocaleDateString("es-ES")}`
            : "Aún no se ha enviado el acceso al portal"}
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          <button onClick={resendAccess} disabled={sending} className="btn btn-ghost shrink-0 text-xs">
            <Send size={13} className="text-zinc-500" />
            {sending ? "Enviando…" : client.portal_access_sent_at ? "Reenviar por email" : "Enviar por email"}
          </button>
          <button onClick={sendPortalWhatsApp} className="btn btn-ghost shrink-0 text-xs">
            <MessageCircle size={13} style={{ color: "#25D366" }} /> Enviar por WhatsApp
          </button>
        </div>
      </div>
    </details>
  );
}
