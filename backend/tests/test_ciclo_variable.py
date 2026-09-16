"""EL CICLO VARIABLE: splits de hasta 10 días y mesociclos de duración libre.

Hasta esta ronda una rutina era SIEMPRE una semana de lunes a domingo y un
mesociclo de cuatro semanas. Estas regresiones cubren las tres cosas que se
rompen en silencio si alguien vuelve a clavar el 7:

  1. QUÉ SESIÓN TOCA HOY. La regla vivía COPIADA en tres sitios y las tres
     daban por DESCANSO cualquier día cuyo nombre no fuera un weekday: con un
     ciclo de 10 días el cliente no vería su entreno NINGÚN día, y sin un error
     en ninguna parte.
  2. EL VOLUMEN. Los guardarraíles comparaban series POR CICLO contra
     landmarks POR SEMANA: un ciclo de 10 días inflaba el recuento un 43 % y
     un plan correcto salía vetado por exceso.
  3. LO QUE LEE EL CLIENTE. Documento, importador de Word y portal tienen que
     llamar «Bloque» a lo que ya no es una semana — y el importador tiene que
     saber reconocer su propia tabla, o el coach edita el Word y sus cambios se
     pierden sin un aviso.

Cada test comprueba además que con `cycle_days = 7` (o ausente, que es como
están TODOS los planes que ya existen) el comportamiento es EXACTAMENTE el de
siempre.
"""
from datetime import date

import pytest

from app.services import training_cycle as tc
from app.services import training_volume as tv


# ============================================ 1 · qué sesión toca hoy ====

def test_sin_cycle_days_el_ciclo_es_la_semana_de_siempre():
    """Todos los planes ya guardados carecen del campo: no pueden cambiar."""
    assert tc.dias_de_ciclo(None) == 7
    assert tc.dias_de_ciclo({}) == 7
    assert tc.dias_de_ciclo({"cycle_days": None}) == 7
    assert tc.dias_de_ciclo({"cycle_days": "basura"}) == 7
    # Y fuera de rango se acota, nunca revienta.
    assert tc.dias_de_ciclo({"cycle_days": 99}) == tc.MAX_DIAS_CICLO
    assert tc.dias_de_ciclo({"cycle_days": 1}) == tc.MIN_DIAS_CICLO


def test_en_la_semana_hoy_se_resuelve_por_el_dia_del_calendario():
    """El cliente que lleva años con su lunes de pecho lo sigue teniendo."""
    training = {"sessions": [{"day": "Miércoles", "name": "Torso"}]}
    miercoles = date(2026, 9, 16)
    assert miercoles.weekday() == 2
    s = tc.sesion_de_fecha(training, miercoles, ancla=date(2026, 9, 1))
    assert s is not None and s["name"] == "Torso"
    # Y el jueves toca descansar.
    assert tc.sesion_de_fecha(training, date(2026, 9, 17), ancla=date(2026, 9, 1)) is None


def test_un_dia_numerico_en_ciclo_semanal_sigue_siendo_basura():
    """Regresión del portal: un `day` numérico en un plan semanal es un JSON a
    medias, no el día 3. Darlo por bueno le enseñaría al cliente la sesión de
    otro día — y es justo lo que pasaba con el matcher permisivo."""
    training = {"sessions": [{"day": 3, "name": "Torso"}]}
    for dia in range(1, 8):
        assert tc.sesion_de_fecha(training, date(2026, 9, dia + 13),
                                  ancla=date(2026, 9, 1)) is None


def test_el_ciclo_de_diez_dias_rota_desde_el_ancla():
    """Lo que antes era imposible: el cliente ve su sesión el día que toca."""
    ancla = date(2026, 9, 1)
    training = {"cycle_days": 10, "sessions": [
        {"day": "Día 1", "day_index": 1, "name": "Empuje"},
        {"day": "Día 4", "day_index": 4, "name": "Pierna"},
        {"day": "Día 9", "day_index": 9, "name": "Espalda"},
    ]}
    vistos = []
    for k in range(20):
        s = tc.sesion_de_fecha(training, ancla.fromordinal(ancla.toordinal() + k),
                               ancla=ancla)
        vistos.append(s["name"] if s else None)
    # Dos vueltas completas e IDÉNTICAS al ciclo: 1, 4 y 9 de cada diez.
    esperado = ["Empuje", None, None, "Pierna", None, None, None, None, "Espalda", None]
    assert vistos == esperado * 2


def test_antes_del_ancla_el_ciclo_aun_no_ha_empezado():
    """Un plan publicado con fecha futura no puede dar un índice negativo."""
    training = {"cycle_days": 10, "sessions": [{"day_index": 1, "name": "A"}]}
    s = tc.sesion_de_fecha(training, date(2026, 8, 20), ancla=date(2026, 9, 1))
    assert s is not None and s["name"] == "A"


def test_las_tres_puertas_de_hoy_dan_la_misma_respuesta():
    """La regla estaba copiada en la pantalla del portal, el recordatorio
    diario y «tu semana». Si vuelven a divergir, una pantalla dirá que hoy
    entrenas y otra que no."""
    from app.services.portal_semana import _nombre_de_la_sesion
    from app.services.push import has_session_on

    ancla = date(2026, 9, 1)
    training = {"cycle_days": 10, "sessions": [{"day": "Día 6", "day_index": 6,
                                                "name": "Pierna"}]}
    for k in range(25):
        hoy = date.fromordinal(ancla.toordinal() + k)
        por_el_nucleo = tc.sesion_de_fecha(training, hoy, ancla=ancla)
        assert has_session_on(training, hoy, ancla=ancla) is (por_el_nucleo is not None)
        assert _nombre_de_la_sesion(training, hoy, ancla=ancla) == (
            por_el_nucleo["name"] if por_el_nucleo else None)


def test_el_bloque_del_mesociclo_es_una_vuelta_al_ciclo():
    ancla = date(2026, 9, 1)
    # Semanal: bloque = semana (lo de siempre).
    assert tc.bloque_de_fecha(ancla, ancla=ancla, ciclo=7, bloques=4) == 0
    assert tc.bloque_de_fecha(date(2026, 9, 8), ancla=ancla, ciclo=7, bloques=4) == 1
    # Ciclo de 10: el bloque 2 empieza el día 11, no el lunes.
    assert tc.bloque_de_fecha(date(2026, 9, 10), ancla=ancla, ciclo=10, bloques=4) == 0
    assert tc.bloque_de_fecha(date(2026, 9, 11), ancla=ancla, ciclo=10, bloques=4) == 1
    # Y al acabar el mesociclo vuelve a empezar.
    assert tc.bloque_de_fecha(date(2026, 10, 11), ancla=ancla, ciclo=10, bloques=4) == 0


def test_las_sesiones_del_ciclo_salen_de_los_dias_por_semana():
    """La anamnesis pregunta lo único que una persona sabe contestar. Cuántas
    sesiones son eso en 10 días lo calcula el backend, no se lo inventa nadie."""
    assert tc.sesiones_objetivo(4, 7) == 4          # ciclo = semana: idéntico
    assert tc.sesiones_objetivo(3, 7) == 3
    assert tc.sesiones_objetivo(4, 10) == 6         # 4/7 × 10 ≈ 5,7
    assert tc.sesiones_objetivo(5, 10) == 7
    assert tc.sesiones_objetivo(6, 3) == 3          # nunca más que el ciclo
    assert tc.sesiones_objetivo(None, 10) >= 1      # sin dato, algo razonable


def test_la_etiqueta_del_dia_y_del_bloque_cambian_con_el_ciclo():
    assert tc.etiqueta_de_dia(1, 7) == "Lunes"
    assert tc.etiqueta_de_dia(1, 10) == "Día 1"
    assert tc.etiqueta_de_bloque(7) == "Semana"
    assert tc.etiqueta_de_bloque(10) == "Bloque"


# ================================================= 2 · volumen y ciclo ====

def test_el_volumen_se_escala_al_ciclo():
    """Series/semana es la unidad de la literatura; el contrato las entrega
    POR CICLO. Sin este escalado, 14 series/semana en un ciclo de 10 días son
    20 y compararlas con el techo semanal da un exceso que no existe."""
    semanal = tv.objetivos_por_grupo(level="intermediate", goal_type="muscle_gain",
                                     cycle_days=7)
    largo = tv.objetivos_por_grupo(level="intermediate", goal_type="muscle_gain",
                                   cycle_days=10)
    assert semanal["groups"]["pecho"]["target"] == 14
    assert largo["groups"]["pecho"]["target"] == 20      # 14 × 10/7, half-up


def test_la_prioridad_sube_el_volumen_de_ese_grupo_y_solo_de_ese():
    """Lo que pidió el dueño: más espalda y hombros DENTRO del ciclo."""
    c = tv.objetivos_por_grupo(level="intermediate", goal_type="muscle_gain",
                               cycle_days=7, priority=["espalda", "hombros"],
                               deprioritized=["gemelos", "biceps"])
    assert c["groups"]["espalda"]["target"] > c["groups"]["pecho"]["target"]
    assert c["groups"]["espalda"]["priority"] is True
    assert c["groups"]["biceps"]["target"] < c["groups"]["pecho"]["target"]
    assert c["groups"]["biceps"]["deprioritized"] is True
    # El mínimo productivo NO se negocia ni desenfatizando: por debajo de ahí
    # el grupo no se mantiene, y eso no es "menos prioridad", es abandonarlo.
    assert c["groups"]["biceps"]["target"] >= tv.SUELO_SEMANA


def test_un_grupo_no_puede_ser_prioritario_y_secundario_a_la_vez():
    c = tv.objetivos_por_grupo(level="intermediate", goal_type="muscle_gain",
                               cycle_days=7, priority=["espalda"],
                               deprioritized=["espalda"])
    assert c["groups"]["espalda"]["priority"] is True
    assert c["groups"]["espalda"]["deprioritized"] is False


def _sesion(dia, idx, ejercicios):
    return {"day": dia, "day_index": idx, "name": "S", "warmup": "x",
            "cooldown": "y", "exercises": ejercicios}


def _ej(eid, sets):
    return {"exercise_id": eid, "sets": sets, "rep_range": "8-12", "rir": "2",
            "rest_sec": 90, "progression_rule": "x", "technique_cue": "y",
            "biomech_cue": "z"}


def test_el_guardarrail_no_veta_por_exceso_un_ciclo_largo_correcto():
    """EL BUG DE FONDO: 30 series de pecho en 10 días son 21/semana (dentro del
    techo), pero contadas como si fueran una semana son un exceso. Sin la
    normalización, cualquier plan de ciclo largo salía vetado."""
    from app.services import guardrails as gr

    lookup = {i: {"id": i, "muscle_primary": "pecho", "muscle_secondary": None,
                  "contraindications": [], "movement_pattern": "horizontal_push",
                  "canonical_name": f"e{i}"} for i in range(1, 7)}
    ejercicios = [_ej(i, 5) for i in range(1, 7)]       # 30 series de pecho
    largo = {"cycle_days": 10, "split_name": "x", "split_rationale": "x",
             "weekly_progression": [], "cardio": {"daily_steps": 8000, "sessions": []},
             "deload_instructions": "x",
             "sessions": [_sesion("Día 1", 1, ejercicios)]}
    rep = gr.check_training(largo, training_days_declared=4, session_max_min=150,
                            client_contraindications=set(), exercise_lookup=lookup)
    # 30 series en 10 días son 21/semana: dentro del techo. Ni un veto.
    assert not any("pecho" in v.lower() for v in rep.violations), rep.violations

    # Y las MISMAS 30 series metidas en una semana sí se vetan: el techo sigue
    # existiendo, solo que en su unidad.
    semanal = {**largo, "cycle_days": 7,
               "sessions": [_sesion("Lunes", 1, ejercicios)]}
    rep2 = gr.check_training(semanal, training_days_declared=4, session_max_min=150,
                             client_contraindications=set(), exercise_lookup=lookup)
    assert any("pecho" in v.lower() for v in rep2.violations), rep2.violations


def test_una_sesion_sin_dia_del_ciclo_es_violacion_solo_si_el_ciclo_rota():
    """En un ciclo rotativo, una sesión sin sitio es una sesión que el cliente
    NO VE ningún día: eso es bloqueante. En el semanal se queda en aviso —
    los planes hechos a mano e importados llevan años publicándose con nombres
    libres y convertirlo en bloqueo rompería el trabajo del coach."""
    from app.services import guardrails as gr

    lookup = {1: {"id": 1, "muscle_primary": "pecho", "muscle_secondary": None,
                  "contraindications": [], "movement_pattern": "horizontal_push",
                  "canonical_name": "e1"}}
    base = {"split_name": "x", "split_rationale": "x", "weekly_progression": [],
            "cardio": {"daily_steps": 8000, "sessions": []},
            "deload_instructions": "x",
            "sessions": [{"day": "Sesión A", "name": "A", "warmup": "x",
                          "cooldown": "y", "exercises": [_ej(1, 3)]}]}
    rota = gr.check_training({**base, "cycle_days": 10}, training_days_declared=3,
                             session_max_min=60, client_contraindications=set(),
                             exercise_lookup=lookup)
    assert any("día" in v.lower() for v in rota.violations), rota.violations

    semanal = gr.check_training({**base, "cycle_days": 7}, training_days_declared=3,
                                session_max_min=60, client_contraindications=set(),
                                exercise_lookup=lookup)
    assert not semanal.violations, semanal.violations


# =================================== 3 · plan a mano, Word y documento ====

def _biblioteca():
    patrones = ["horizontal_push", "vertical_push", "horizontal_pull",
                "vertical_pull", "squat", "hip_hinge", "lunge", "knee_extension",
                "knee_flexion", "elbow_extension", "elbow_flexion",
                "core_anti_extension", "core_anti_rotation", "shoulder_abduction",
                "calf", "hip_abduction"]
    lib, i = [], 0
    for p in patrones:
        for k in range(4):
            i += 1
            lib.append({"id": i, "movement_pattern": p, "level_min": 1,
                        "canonical_name": f"{p} {k}", "technique_notes": None,
                        "biomechanics_notes": None})
    return lib


class _Cli:
    def __init__(self, **kw):
        self.training_days = 5
        self.session_max_min = 60
        self.daily_activity_level = "active"
        self.cycle_days = None
        self.mesocycle_blocks = None
        self.__dict__.update(kw)


@pytest.mark.parametrize("ciclo,bloques,sesiones_esperadas", [
    (None, None, 5),     # lo de siempre: 5 días/semana → 5 sesiones, 4 semanas
    (10, 5, 7),          # 5/7 × 10 ≈ 7 sesiones en el ciclo
    (3, 2, 2),
])
def test_el_plan_a_mano_construye_el_ciclo_pedido(ciclo, bloques, sesiones_esperadas):
    from app.schemas.ai import TrainingCore
    from app.services import plan_scaffold as ps

    tr = ps.build_training(_Cli(cycle_days=ciclo, mesocycle_blocks=bloques),
                           _biblioteca())
    TrainingCore.model_validate(tr)                      # pasa el contrato
    assert tr["cycle_days"] == (ciclo or 7)
    assert len(tr["sessions"]) == sesiones_esperadas
    assert len(tr["weekly_progression"]) == (bloques or 4)
    # Los días caben en el ciclo y no se repiten.
    dias = [s["day_index"] for s in tr["sessions"]]
    assert len(set(dias)) == len(dias)
    assert all(1 <= d <= (ciclo or 7) for d in dias)
    # Y la sesión de cada día se localiza por la puerta única.
    for s in tr["sessions"]:
        assert tc.indice_de_dia(s, tr["cycle_days"]) == s["day_index"]


def test_un_mesociclo_corto_no_promete_una_descarga_que_no_existe():
    """Con 2 bloques no hay margen para descargar (sería la mitad del tiempo),
    así que la progresión no la pone — y el texto no puede decir lo contrario."""
    from app.services import plan_scaffold as ps

    corto = ps.build_training(_Cli(mesocycle_blocks=2), _biblioteca())
    assert not any(p["intent"] == "Deload" for p in corto["weekly_progression"])
    assert "descarga" in corto["deload_instructions"].lower()
    assert "no lleva descarga programada" in corto["deload_instructions"]

    largo = ps.build_training(_Cli(mesocycle_blocks=6), _biblioteca())
    assert largo["weekly_progression"][-1]["intent"] == "Deload"
    assert largo["deload_instructions"].startswith("Semana 6:")


def test_el_documento_y_el_importador_de_word_hablan_el_mismo_idioma():
    """⚠️ La cabecera de la tabla de progresión la reconoce `word_import` por
    FIRMA. Al titularla «Bloque» en un ciclo rotativo, sin la segunda firma el
    importador no reconocería su propia tabla: el coach editaría el Word, lo
    subiría, se le diría «aplicado» y sus cambios se habrían perdido."""
    import io

    from docx import Document

    from app.services import plan_scaffold as ps
    from app.services import word_import as wi
    from app.services.docs.plan_doc import generate_plan_doc
    from app.services.docs.word_base import DocBrand

    brand = DocBrand(name="DQR", color_primary="#8B1A2B",
                     color_secondary="#4A7BA8", font_family="Calibri")
    nut = {"tdee_kcal": 2500, "target_kcal": 2200,
           "macros": {"carbs_g": 200, "protein_g": 170, "fat_g": 70},
           "meals": [{"slot": 1, "name": "Desayuno", "time": "08:00"}],
           "meal_bank": {"mode": "flexible", "slots": []}}
    lib = _biblioteca()
    nombres = {e["id"]: e["canonical_name"] for e in lib}

    for ciclo, firma in ((7, wi.SIG_PROGRESION), (10, wi.SIG_PROGRESION_BLOQUE)):
        tr = ps.build_training(_Cli(cycle_days=ciclo, mesocycle_blocks=4), lib)
        data = generate_plan_doc(
            brand=brand, client_name="Mario", month_index=1, goal_type="fat_loss",
            diet_mode="flexible", nutrition=nut, training=tr, education={},
            include_training=True, include_nutrition=True, exercise_names=nombres)
        doc = Document(io.BytesIO(data))
        firmas = [wi._header_sig(t) for k, t in wi._iter_blocks(doc) if k == "t"]
        assert firma in firmas, (ciclo, firmas)
        # Y la caja de la descarga se ancla a una barra que el importador
        # traduce (`_ALIAS_BARRA`), llame como llame el documento a la vuelta.
        barras = [b.text.strip() for k, b in wi._iter_blocks(doc)
                  if k == "p" and wi._es_barra(b)]
        descarga = [b for b in barras if "DESCARGA" in b.upper()]
        assert descarga, barras
        assert wi._barra_canonica(wi._norm(descarga[0])).startswith(
            "semana de descarga")


def test_el_plan_importado_de_un_documento_ajeno_usa_el_ciclo_de_la_ficha():
    """El papel trae ejercicios y series; la ESTRUCTURA la decide el coach en
    la ficha. Un «lunes» escrito en un documento no significa nada dentro de un
    ciclo de 10 días."""
    from app.services import plan_import as pi

    etiqueta, idx = pi._dia_sesion("lunes", 0, 3, 7)
    assert (etiqueta, idx) == ("Lunes", 1)
    etiqueta, idx = pi._dia_sesion("lunes", 0, 3, 10)
    assert etiqueta.startswith("Día") and 1 <= idx <= 10


def test_el_panel_de_revision_ve_el_ciclo_entero():
    """Se cortaba en 7 sesiones. Con un ciclo de 10, las tres últimas no las
    veía NINGÚN revisor — y uno de ellos, el clínico, tiene VETO."""
    from app.services.plan_review import _plan_text

    tr = {"cycle_days": 10, "split_name": "X", "weekly_progression": [{"week": 1}],
          "sessions": [{"day": f"Día {i}", "name": f"S{i}",
                        "exercises": [{"exercise_id": 1, "sets": 3}]}
                       for i in range(1, 11)]}
    texto = _plan_text({}, tr, {1: "Press banca"})
    for i in range(1, 11):
        assert f"S{i}" in texto, f"falta la sesión {i}"
    assert "ciclo de 10 días" in texto


# ================================== 4 · duración de la revisión (7-31) ====

def test_la_revision_dura_lo_que_diga_la_ficha():
    from app.services.periods import PERIOD_DAYS, review_days

    class C:
        review_days = None

    assert review_days(C()) == PERIOD_DAYS
    assert review_days(None) == PERIOD_DAYS
    C.review_days = 21
    assert review_days(C()) == 21
    C.review_days = 900                       # fuera de rango → acotado
    assert review_days(C()) == 31
    C.review_days = "basura"
    assert review_days(C()) == PERIOD_DAYS


def test_los_umbrales_de_riesgo_se_escalan_con_la_revision():
    """«Adherencia a día 10» y «empujón el día 12» se fijaron sobre catorce
    días. Clavados, en una revisión semanal el empujón no llegaba NUNCA (el
    período ya habría cerrado) y en una mensual saltaba a un tercio del camino,
    cuando aún no hay nada que reprochar."""
    from app.services.state_machine import (LOG_RATIO_CHECK_DAY, REMINDER_DAY,
                                            _umbral)

    assert _umbral(REMINDER_DAY, None) == REMINDER_DAY       # sin dato, igual
    assert _umbral(REMINDER_DAY, 14) == REMINDER_DAY         # la quincena, igual
    assert _umbral(REMINDER_DAY, 7) == 6                     # cabe en la semana
    assert _umbral(REMINDER_DAY, 28) == 24
    assert _umbral(LOG_RATIO_CHECK_DAY, 28) == 20


def test_el_cierre_se_abre_el_ultimo_dia_del_periodo():
    """Era «el día 14» y fallaba por los dos lados: un período de 13 días dejaba
    al cliente sin poder enviar su revisión NUNCA, y uno de 21 se la abría una
    semana antes de tiempo."""
    from types import SimpleNamespace

    from app.services.portal import period_info

    def info(total, transcurridos):
        inicio = date(2026, 9, 1)
        p = SimpleNamespace(id=1, period_index=1, starts_on=inicio,
                            ends_on=date.fromordinal(inicio.toordinal() + total - 1),
                            status="open")
        return period_info(p, date.fromordinal(inicio.toordinal() + transcurridos))

    assert info(14, 12)["can_close"] is False
    assert info(14, 13)["can_close"] is True            # día 14: lo de siempre
    assert info(13, 12)["can_close"] is True            # el corto, desbloqueado
    assert info(21, 13)["can_close"] is False           # el largo, aún no
    assert info(21, 20)["can_close"] is True
