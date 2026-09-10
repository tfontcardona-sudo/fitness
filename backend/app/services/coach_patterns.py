"""LOS PATRONES DEL COACH: qué hace SIEMPRE, sin gastar un crédito.

El aprendizaje de §13 destilaba lecciones con la IA a partir de las últimas
ediciones. Servía para el tono, pero no respondía a lo que el coach quiere
saber de verdad: *qué campo toco yo siempre*, *qué cambio por qué*, y *qué
parte del plan no toco nunca*. Eso NO necesita un modelo: son cuentas sobre las
filas de `plan_edits`, y las cuentas las hace el backend.

Tres cosas salen de aquí:

1. **Campos que siempre editas.** Por señal (`nutricion.kcal`,
   `entreno.ejercicio`…), cuántas veces y sobre cuántos planes distintos. Un
   campo tocado en 9 de tus 10 últimos planes es una decisión tuya que el
   sistema todavía no sabe tomar.
2. **Sustituciones repetidas.** "Sentadilla búlgara → Prensa" cinco veces es una
   preferencia, no una casualidad.
3. **Lo que NO tocas.** El complemento: los campos que sobreviven intactos son
   los que un MODELO puede dar por buenos.

Y con eso, `sugerencia_de_modelo` propone el modelo de plan que el coach
describiría a mano: fija lo estable y deja abierto lo que siempre acaba
cambiando, para no tener que volver a cambiarlo.

ACUMULA. No hay ventana que borre lo aprendido: los patrones se cuentan sobre
todo el historial, y la fecha del último caso dice si el patrón sigue vivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Plan, PlanEdit
from app.services.continuous_learning import etiqueta_de_signal

# Un patrón necesita repetirse para serlo. Con 2 veces cualquier casualidad
# parece una costumbre; con 3 ya cuesta explicarla por azar.
MIN_REPETICIONES = 3
# …y en al menos este número de planes DISTINTOS: cinco correcciones seguidas
# sobre el mismo plan son una tarde de trabajo, no una costumbre.
MIN_PLANES = 2
# Cuántos planes recientes se miran para decir "en X de tus últimos Y".
VENTANA_PLANES = 12


@dataclass
class PatronCampo:
    """Un campo que el coach edita una y otra vez."""

    signal: str
    etiqueta: str
    veces: int
    planes: int                 # en cuántos planes DISTINTOS lo tocó
    ultima: datetime | None
    origenes: dict = field(default_factory=dict)   # {source: veces}

    @property
    def vivo(self) -> bool:
        """¿Sigue pasando? Un patrón de hace ocho meses ya no describe al coach
        de hoy: se enseña, pero no se le propone como si fuera de ayer."""
        if self.ultima is None:
            return False
        return (datetime.now(timezone.utc) - self.ultima) <= timedelta(days=120)


@dataclass
class PatronSustitucion:
    """"Siempre cambias X por Y."""

    de: str
    a: str
    veces: int
    signal: str
    ultima: datetime | None


def _norm(texto: str) -> str:
    import unicodedata

    return " ".join(
        unicodedata.normalize("NFKD", texto or "")
        .encode("ascii", "ignore").decode("ascii").lower().split())


def _filtro_cartera(db: Session):
    """Los planes de la marca ACTIVA. Cada negocio aprende de lo suyo."""
    from app.services.branding import cartera_de_la_marca

    return cartera_de_la_marca(db)


def _planes_de_la_marca(db: Session):
    """Subconsulta con los ids de plan que cuentan para esta marca."""
    from app.models import Client

    cartera = _filtro_cartera(db)
    q = select(Plan.id)
    if cartera is not None:
        q = q.join(Client, Client.id == Plan.client_id).where(cartera)
    return q


def campos_recurrentes(db: Session, *, min_veces: int = MIN_REPETICIONES,
                       min_planes: int = MIN_PLANES) -> list[PatronCampo]:
    """Campos que el coach corrige una y otra vez, del más al menos frecuente."""
    filas = db.execute(
        select(PlanEdit.signal,
               func.count(PlanEdit.id),
               func.count(func.distinct(PlanEdit.plan_id)),
               func.max(PlanEdit.created_at))
        .where(PlanEdit.signal.is_not(None), PlanEdit.signal != "otro",
               PlanEdit.plan_id.in_(_planes_de_la_marca(db)))
        .group_by(PlanEdit.signal)
    ).all()
    # Los ORÍGENES de cada señal, en una sola consulta más (no una por señal).
    por_origen: dict[str, dict[str, int]] = {}
    for signal, source, n in db.execute(
        select(PlanEdit.signal, PlanEdit.source, func.count(PlanEdit.id))
        .where(PlanEdit.signal.is_not(None),
               PlanEdit.plan_id.in_(_planes_de_la_marca(db)))
        .group_by(PlanEdit.signal, PlanEdit.source)
    ).all():
        por_origen.setdefault(signal, {})[source or "edicion"] = int(n)

    out = [
        PatronCampo(signal=signal, etiqueta=etiqueta_de_signal(signal),
                    veces=int(veces), planes=int(planes), ultima=ultima,
                    origenes=por_origen.get(signal, {}))
        for signal, veces, planes, ultima in filas
        if int(veces) >= min_veces and int(planes) >= min_planes
    ]
    out.sort(key=lambda p: (-p.veces, p.signal))
    return out


def sustituciones_recurrentes(db: Session, *, min_veces: int = MIN_REPETICIONES
                              ) -> list[PatronSustitucion]:
    """"Cambias X por Y" que se repite. Se agrupa por la pareja NORMALIZADA
    (sin acentos ni mayúsculas): "Sentadilla búlgara" y "sentadilla bulgara"
    son la misma preferencia escrita de dos formas."""
    filas = db.execute(
        select(PlanEdit.detail, PlanEdit.signal, PlanEdit.created_at)
        .where(PlanEdit.detail.is_not(None),
               PlanEdit.plan_id.in_(_planes_de_la_marca(db)))
    ).all()
    agrupado: dict[tuple[str, str], dict] = {}
    for detail, signal, cuando in filas:
        if "→" not in (detail or ""):
            continue
        de, a = [x.strip() for x in detail.split("→", 1)]
        if not de or not a:
            continue
        clave = (_norm(de), _norm(a))
        g = agrupado.setdefault(clave, {"de": de, "a": a, "veces": 0,
                                        "signal": signal or "otro", "ultima": None})
        g["veces"] += 1
        if g["ultima"] is None or (cuando and cuando > g["ultima"]):
            g["ultima"] = cuando
    out = [PatronSustitucion(de=g["de"], a=g["a"], veces=g["veces"],
                             signal=g["signal"], ultima=g["ultima"])
           for g in agrupado.values() if g["veces"] >= min_veces]
    out.sort(key=lambda p: (-p.veces, p.de))
    return out


def campos_estables(db: Session, *, ventana: int = VENTANA_PLANES) -> list[str]:
    """Señales que NO aparecen en las ediciones de los últimos planes.

    Es el complemento de lo anterior y es lo que hace útil un modelo: si en tus
    últimos doce planes no has tocado nunca el cardio, el cardio del modelo
    puede ir fijado y no te hará perder tiempo."""
    from app.services.continuous_learning import SIGNAL_LABELS

    recientes = [
        pid for (pid,) in db.execute(
            select(Plan.id).where(Plan.id.in_(_planes_de_la_marca(db)))
            .order_by(Plan.id.desc()).limit(max(1, ventana))
        ).all()
    ]
    if not recientes:
        return []
    tocadas = {
        s for (s,) in db.execute(
            select(PlanEdit.signal).where(PlanEdit.plan_id.in_(recientes),
                                          PlanEdit.signal.is_not(None)).distinct()
        ).all()
    }
    return [s for s in SIGNAL_LABELS if s != "otro" and s not in tocadas]


def resumen(db: Session) -> dict:
    """Todo lo aprendido, listo para la pantalla de Aprendizaje y para el
    prompt de generación. Cero llamadas a la IA."""
    campos = campos_recurrentes(db)
    subs = sustituciones_recurrentes(db)
    estables = campos_estables(db)
    total = int(db.scalar(
        select(func.count(PlanEdit.id))
        .where(PlanEdit.plan_id.in_(_planes_de_la_marca(db)))) or 0)
    return {
        "ediciones_totales": total,
        "campos": [
            {"signal": c.signal, "etiqueta": c.etiqueta, "veces": c.veces,
             "planes": c.planes, "vivo": c.vivo,
             "ultima": c.ultima.isoformat() if c.ultima else None,
             "origenes": c.origenes,
             "frase": _frase_campo(c)}
            for c in campos
        ],
        "sustituciones": [
            {"de": s.de, "a": s.a, "veces": s.veces, "signal": s.signal,
             "etiqueta": etiqueta_de_signal(s.signal),
             "frase": f"Cambias «{s.de}» por «{s.a}» ({s.veces} veces)"}
            for s in subs
        ],
        "estables": [{"signal": s, "etiqueta": etiqueta_de_signal(s)} for s in estables],
        "min_repeticiones": MIN_REPETICIONES,
    }


def _frase_campo(c: PatronCampo) -> str:
    """El patrón dicho como se lo diría una persona al coach."""
    donde = {
        "copia": "sobre planes copiados",
        "modelo": "sobre modelos aplicados",
        "documento": "sobre planes importados",
        "word": "desde el Word",
    }
    origen_top = max(c.origenes.items(), key=lambda kv: kv[1])[0] if c.origenes else ""
    matiz = f" (sobre todo {donde[origen_top]})" if origen_top in donde else ""
    return (f"Ajustas {c.etiqueta} en {c.planes} planes distintos "
            f"({c.veces} veces){matiz}.")


def bloque_para_prompt(db: Session, *, max_lineas: int = 8) -> str:
    """Los patrones, en el USER prompt de generación ('' si aún no hay).

    Va aparte de las LECCIONES (que las redacta la IA): esto son hechos
    contados, no interpretaciones, y por eso puede afirmarse sin matices. No
    cuesta créditos generarlo y va en el user prompt para no invalidar la caché
    del system."""
    try:
        datos = resumen(db)
    except Exception:  # noqa: BLE001 — el aprendizaje jamás bloquea generar
        return ""
    lineas: list[str] = []
    for s in datos["sustituciones"][:max_lineas // 2]:
        lineas.append(f"- Prefiere «{s['a']}» antes que «{s['de']}».")
    for c in datos["campos"][:max_lineas]:
        if c["vivo"]:
            lineas.append(f"- Suele corregir {c['etiqueta']}: aféinalo desde el principio.")
        if len(lineas) >= max_lineas:
            break
    if not lineas:
        return ""
    return ("\n\nCOSTUMBRES DEL COACH (contadas de sus correcciones reales; "
            "respétalas SIN cambiar ningún número del contrato):\n"
            + "\n".join(lineas[:max_lineas]))


# ------------------------------------------------- el modelo que te ahorra ----

def sugerencia_de_modelo(db: Session) -> dict | None:
    """El MODELO de plan que el coach se haría a mano si tuviera tiempo.

    La idea, en sus palabras: «como veo que haces mucho esto, te creo un modelo
    con esto igual, pero esto para editar, ya que siempre lo editas».

    De un plan REAL suyo (el último que dejó activo) se toma la estructura, y
    encima se marcan dos listas:

    - **fijo**: lo que no ha tocado en sus últimos planes. Va tal cual.
    - **abierto**: lo que corrige una y otra vez. No se adivina un valor —eso
      sería inventarle criterio—: se señala para que lo revise nada más aplicar
      el modelo, que es exactamente el trabajo que hoy hace a ciegas.

    Devuelve None si todavía no hay material: sin patrones, un modelo
    "inteligente" sería un modelo cualquiera con un nombre pretencioso.
    """
    datos = resumen(db)
    campos_vivos = [c for c in datos["campos"] if c["vivo"]]
    if not campos_vivos:
        return None

    base = db.scalar(
        select(Plan)
        .where(Plan.id.in_(_planes_de_la_marca(db)), Plan.status == "published")
        .order_by(Plan.id.desc()).limit(1)
    )
    if base is None:
        return None

    abierto = [{"signal": c["signal"], "etiqueta": c["etiqueta"], "veces": c["veces"]}
               for c in campos_vivos[:6]]
    señales_abiertas = {c["signal"] for c in abierto}
    fijo = [e for e in datos["estables"] if e["signal"] not in señales_abiertas][:8]

    titulo = _titulo_sugerido(base, abierto)
    return {
        "plan_id": base.id,
        "titulo": titulo,
        "porque": (
            "Sale de tus propias correcciones: "
            + "; ".join(f"{c['etiqueta']} ({c['veces']} veces)" for c in abierto[:3])
            + "."),
        "abierto": abierto,
        "fijo": fijo,
        "resumen": _resumen_de_plan(base),
    }


def _titulo_sugerido(plan: Plan, abierto: list[dict]) -> str:
    """Un título que diga de qué es el modelo, no "Modelo 4"."""
    tr = plan.training_json or {}
    dias = len(tr.get("sessions") or [])
    split = (tr.get("split_name") or "").strip()
    partes = [p for p in (split, f"{dias} días" if dias else "") if p]
    cabeza = " · ".join(partes) or "Modelo"
    return f"{cabeza} · a tu manera"[:120]


def _resumen_de_plan(plan: Plan) -> str:
    nut = plan.nutrition_json or {}
    tr = plan.training_json or {}
    kcal = nut.get("target_kcal")
    dias = len(tr.get("sessions") or [])
    trozos = []
    if kcal:
        trozos.append(f"{int(kcal):,}".replace(",", ".") + " kcal")
    if dias:
        trozos.append(f"{dias} días")
    if tr.get("split_name"):
        trozos.append(str(tr["split_name"]))
    return " · ".join(trozos)[:200]


def nota_del_modelo(sug: dict) -> str:
    """El aviso que acompaña al modelo creado: qué revisar nada más aplicarlo.
    Se guarda en el propio modelo para que dentro de tres meses siga diciendo
    por qué está hecho así."""
    if not sug or not sug.get("abierto"):
        return ""
    partes = ", ".join(c["etiqueta"] for c in sug["abierto"])
    return (f"Revisa al aplicarlo: {partes}. "
            "Es lo que corriges siempre, así que el modelo no lo da por bueno.")
