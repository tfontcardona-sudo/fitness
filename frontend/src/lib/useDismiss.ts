import { useEffect, useRef, type RefObject } from "react";

/**
 * Cierre consistente de CUALQUIER overlay (desplegable, modal, popover):
 *
 * - Tap/click FUERA del elemento → se cierra. El listener va en fase de
 *   CAPTURA sobre `pointerdown`, así el overlay se cierra ANTES de que el
 *   click llegue a su destino: una sola pulsación cierra Y ejecuta la acción
 *   de destino (nunca "cerrar primero, pulsar después").
 * - Tecla ESC → se cierra.
 * - Cambio de ruta/pestaña → el componente se desmonta y el efecto se limpia
 *   solo (los overlays del portal viven dentro del contenido de cada pestaña).
 *
 * Único punto de verdad: nada de lógica duplicada por componente.
 */
export function useDismiss(
  ref: RefObject<HTMLElement | null>,
  onDismiss: () => void,
  active = true,
) {
  useEffect(() => {
    if (!active) return;
    const onPointer = (e: PointerEvent) => {
      const el = ref.current;
      if (el && e.target instanceof Node && !el.contains(e.target)) onDismiss();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDismiss();
    };
    document.addEventListener("pointerdown", onPointer, true);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer, true);
      document.removeEventListener("keydown", onKey);
    };
  }, [ref, onDismiss, active]);
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Gestión de foco para modales: al abrir, guarda el elemento que tenía el foco
 * y enfoca el primero enfocable del modal; mientras está abierto, Tab/Shift+Tab
 * quedan atrapados dentro; al cerrar, el foco vuelve al elemento que lo abrió.
 */
export function useModalFocus(ref: RefObject<HTMLElement | null>, open: boolean) {
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const el = ref.current;
    if (el) {
      const first = el.querySelector<HTMLElement>(FOCUSABLE);
      (first ?? el).focus();
    }
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !ref.current) return;
      const items = Array.from(ref.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      opener.current?.focus();
    };
  }, [ref, open]);
}
