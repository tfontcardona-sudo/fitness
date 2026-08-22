"""Cada aviso debe saber DÓNDE se arregla y CÓMO.

Sin esto, "pulsa el aviso y te lleva al sitio exacto" no puede funcionar: el
panel se queda con el texto y sin destino. También se comprueba que la clave
del problema es estable (el recordatorio se ancla por ella y se borra solo
cuando deja de aparecer) y que no colisiona entre problemas distintos.
"""
from __future__ import annotations

import inspect

from app.routers import alerts as al


def test_todo_destino_declarado_tiene_ancla_y_como_arreglarlo():
    for kind, (target, fix) in al._DESTINO.items():
        assert target and not target.endswith("."), f"{kind}: ancla vacía o rota"
        assert " " not in target, f"{kind}: el ancla no puede llevar espacios"
        assert fix and len(fix) > 15, f"{kind}: falta explicar cómo se arregla"
        assert fix[0].isupper(), f"{kind}: la nota empieza en minúscula"
        assert fix.rstrip().endswith((".", "!")), f"{kind}: la nota sin cerrar"


def test_los_kinds_del_codigo_estan_cubiertos():
    """Si se añade un aviso nuevo y se olvida su destino, salta aquí."""
    fuente = inspect.getsource(al)
    kinds = set()
    for linea in fuente.splitlines():
        if '_alert(' in linea or 'client, "' in linea:
            for trozo in linea.split('"'):
                if trozo.replace("_", "").isalnum() and "_" in trozo and trozo.islower():
                    kinds.add(trozo)
    # Los que dependen de un dato concreto pasan el ancla en la llamada, no en
    # el mapa: no se exigen aquí.
    dinamicos = {"plan_allergen_conflict", "plan_dislike_conflict",
                 "video_call_proposed", "video_call_manual",
                 "video_call_tomorrow", "video_call_confirm"}
    conocidos = set(al._DESTINO) | dinamicos
    huerfanos = {k for k in kinds if k.endswith(("_plan", "_feedback", "_review",
                                                 "_pending", "_due", "_logs",
                                                 "_request", "_products",
                                                 "_inactive", "_overdue",
                                                 "_conflict", "_inputs"))} - conocidos
    assert not huerfanos, f"avisos sin destino declarado: {sorted(huerfanos)}"


def _cliente_falso(**extra):
    class C:
        id = 42
        full_name = "Carla Ruiz"
    for k, v in extra.items():
        setattr(C, k, v)
    return C()


def test_la_clave_identifica_el_problema_y_no_colisiona():
    c = _cliente_falso()
    a = al._alert(c, "adapt_plan", "alta", "x", "planificacion", "Adaptar")
    b = al._alert(c, "publish_plan", "alta", "x", "planificacion", "Activar")
    assert a["key"] != b["key"], "dos problemas distintos con la misma clave"
    # Estable: el mismo problema, la misma clave (aunque cambie la redacción).
    otra_vez = al._alert(c, "adapt_plan", "alta", "OTRO TEXTO", "planificacion", "Adaptar")
    assert a["key"] == otra_vez["key"], "la clave cambia si se reescribe el aviso"
    assert a["target"] and a["fix"], "el aviso no dice dónde ni cómo"


def test_dos_alergenos_en_tomas_distintas_son_dos_problemas():
    c = _cliente_falso()
    t2 = al._alert(c, "plan_allergen_conflict", "alta", "x", "planificacion",
                   "Corregir", target="nutricion.comida.2", fix="Aquí.")
    t3 = al._alert(c, "plan_allergen_conflict", "alta", "x", "planificacion",
                   "Corregir", target="nutricion.comida.3", fix="Aquí.")
    assert t2["key"] != t3["key"], "el ancla debe entrar en la clave"


def test_un_aviso_sin_destino_no_inventa_ninguno():
    c = _cliente_falso()
    a = al._alert(c, "kind_que_no_existe", "media", "x", "resumen", "Ver")
    assert a["target"] is None and a["fix"] is None
    assert a["key"] == "42:kind_que_no_existe:"


def test_el_objetivo_se_valora_donde_se_resuelve_de_verdad():
    """Cambiar el campo en la ficha NO pospone el aviso ni regenera el plan
    (solo enciende otro aviso), y ese campo vive dentro del modo edición, así
    que el ancla ni siquiera existía al llegar. La decisión se toma en la
    tarjeta de etapa de Planificación."""
    target, _ = al._DESTINO["goal_review"]
    assert target == "plan.objetivo", target


def test_los_avisos_con_plan_publicado_no_apuntan_a_la_vista_sin_plan():
    """`plan.generar` solo existe en la pantalla de "aún no hay plan", y estos
    avisos exigen por definición un plan PUBLICADO: apuntar ahí era mandar al
    coach a un ancla que no puede existir."""
    for kind in ("regenerate_goal", "plan_stale_inputs", "goal_review"):
        target, _ = al._DESTINO[kind]
        assert target != "plan.generar", kind
