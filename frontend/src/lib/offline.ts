import { useEffect, useState } from "react";

/**
 * ¿Hay conexión?
 *
 * El cliente entrenando en el sótano del gimnasio seguía tecleando series
 * mientras cada guardado fallaba, y solo se enteraba por un toast suelto que
 * se iba a los cuatro segundos. El coach, igual con el portátil en el metro.
 *
 * `navigator.onLine` miente en un sentido (dice "sí" con wifi conectado pero
 * sin salida a internet) y acierta en el otro: cuando dice "no", no hay nada
 * que hacer. Se usa solo para AVISAR, nunca para bloquear: si el navegador se
 * equivoca, el cliente sigue pudiendo teclear y el autosave reintenta.
 */
export function useSinConexion(): boolean {
  const [sinConexion, setSinConexion] = useState(
    () => typeof navigator !== "undefined" && navigator.onLine === false,
  );
  useEffect(() => {
    const fuera = () => setSinConexion(true);
    const dentro = () => setSinConexion(false);
    window.addEventListener("offline", fuera);
    window.addEventListener("online", dentro);
    return () => {
      window.removeEventListener("offline", fuera);
      window.removeEventListener("online", dentro);
    };
  }, []);
  return sinConexion;
}
