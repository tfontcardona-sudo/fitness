"""Una respuesta cortada por longitud no es "JSON mal formado".

Cuando el modelo llega al techo de `max_tokens`, el JSON llega TRUNCADO y el
parser falla. El cliente lo trataba como un error de formato y reintentaba con
el MISMO prompt y el MISMO techo: se cortaba en el mismo sitio, se pagaban las
DOS llamadas enteras (la parte cara del sistema) y el fallo era seguro. Encima
el mensaje decía "JSON mal formado", que manda a buscar el fallo donde no está.
"""
import warnings

import pytest
from pydantic import BaseModel

warnings.filterwarnings("ignore")


class _Salida(BaseModel):
    texto: str


class _Bloque:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, texto, stop_reason):
        self.content = [_Bloque(texto)]
        self.stop_reason = stop_reason
        self.usage = None


def _cliente(respuestas):
    """AIClient real, pero con la llamada a la API sustituida: devuelve las
    respuestas de la lista y anota con qué `max_tokens` se pidió cada una."""
    from app.services.ai.client import AIClient

    cli = AIClient(api_key="sk-test")
    llamadas = []

    def _create(kwargs):
        llamadas.append(kwargs)
        return respuestas[len(llamadas) - 1]

    cli._create_message = _create           # type: ignore[method-assign]
    cli._record_usage = staticmethod(lambda *a, **k: None)  # type: ignore[assignment]
    return cli, llamadas


def test_una_respuesta_cortada_reintenta_con_mas_techo_y_pidiendo_brevedad():
    cli, llamadas = _cliente([
        _Resp('{"texto": "aaaa', "max_tokens"),        # truncada
        _Resp('{"texto": "ok"}', "end_turn"),          # a la segunda, entera
    ])
    out = cli.generate_json(model="m", system="s", user="u", schema=_Salida,
                            max_tokens=1000)
    assert out.texto == "ok"
    assert len(llamadas) == 2
    # El techo SUBE (antes se repetía idéntico y se cortaba en el mismo sitio).
    assert llamadas[1]["max_tokens"] > llamadas[0]["max_tokens"]
    # Y se le pide que sea más compacto, no que "corrija el formato".
    segundo = llamadas[1]["messages"][0]["content"]
    assert "se quedó A MEDIAS" in segundo and "COMPACTO" in segundo
    assert "JSON mal formado" not in segundo


def test_el_techo_del_reintento_no_se_dispara_sin_limite():
    from app.services.ai.client import MAX_TOKENS_TECHO

    cli, llamadas = _cliente([
        _Resp('{"texto": "aa', "max_tokens"),
        _Resp('{"texto": "bb', "max_tokens"),
    ])
    with pytest.raises(Exception) as exc:
        cli.generate_json(model="m", system="s", user="u", schema=_Salida,
                          max_tokens=MAX_TOKENS_TECHO)
    assert llamadas[1]["max_tokens"] == MAX_TOKENS_TECHO
    # Y el error dice la VERDAD: se cortó, no es un formato malo.
    assert "CORT" in str(exc.value).upper()


def test_un_json_de_verdad_malformado_sigue_reintentando_como_siempre():
    """Sin corte, el camino de siempre: mismo techo y el error inyectado."""
    cli, llamadas = _cliente([
        _Resp("esto no es json", "end_turn"),
        _Resp('{"texto": "ok"}', "end_turn"),
    ])
    assert cli.generate_json(model="m", system="s", user="u", schema=_Salida,
                             max_tokens=1000).texto == "ok"
    assert llamadas[1]["max_tokens"] == llamadas[0]["max_tokens"] == 1000
    assert "falló la validación" in llamadas[1]["messages"][0]["content"]


# ---------------------------------------------------------------------------
# Lo que ven los revisores del panel §9
# ---------------------------------------------------------------------------

def test_los_revisores_ven_los_ejercicios_por_su_nombre_no_un_recuento():
    """El panel tiene roles cuya rúbrica es literalmente "selección y ORDEN de
    ejercicios" y solo recibían el RECUENTO ("6 ejercicios, 18 series"): con
    eso no se puede juzgar si el plan repite patrón, si el aislamiento va antes
    que el básico o si toca una lesión declarada. Se pagaban a ciegas."""
    from app.services.plan_review import _plan_text

    training = {
        "split_name": "Torso/Pierna",
        "sessions": [{
            "day": "Lunes", "name": "Torso A",
            "exercises": [
                {"exercise_id": 7, "sets": 4, "rep_range": "6-8", "rir": "2",
                 "rest_sec": 120},
                {"exercise_id": 9, "sets": 3, "rep_range": "10-12", "rir": "1-2"},
            ],
        }],
    }
    nombres = {7: "Press banca con barra", 9: "Remo con mancuerna"}
    texto = _plan_text({"target_kcal": 2000, "macros": {}}, training, nombres)

    assert "Press banca con barra" in texto
    assert "Remo con mancuerna" in texto
    assert "4×6-8" in texto and "RIR 2" in texto
    # El recuento sigue estando (da el volumen de un vistazo).
    assert "2 ejercicios" in texto


def test_sin_biblioteca_el_ejercicio_sale_por_su_id_y_no_desaparece():
    """Si la traducción no está disponible, mejor "ejercicio #7" que nada: el
    revisor al menos ve CUÁNTOS y en qué orden."""
    from app.services.plan_review import _plan_text

    training = {"split_name": "x", "sessions": [{
        "day": "Lunes", "name": "A",
        "exercises": [{"exercise_id": 7, "sets": 4, "rep_range": "6-8", "rir": "2"}]}]}
    assert "ejercicio #7" in _plan_text({"target_kcal": 2000, "macros": {}}, training, None)


def test_la_biblioteca_de_ejercicios_viaja_cacheada_y_no_se_repaga():
    """Era el bloque más gordo del prompt del núcleo (cientos de ejercicios) y
    vivía en el USER prompt, que no se cachea: el reintento por validación lo
    repagaba ENTERO. Ahora va como segundo bloque de system con `cache_control`
    — el primero (el prompt fijo) se sigue cacheando entre clientes y este,
    específico del cliente, se lee al 10% en su reintento."""
    from types import SimpleNamespace

    from app.services.ai.generator import _biblioteca_block, _system_con_biblioteca

    ctx = SimpleNamespace(exercise_library=[
        {"id": 7, "canonical_name": "Press banca", "movement_pattern": "empuje_horizontal",
         "muscle_primary": "pecho"},
        {"id": 9, "canonical_name": "Remo", "movement_pattern": "traccion_horizontal",
         "muscle_primary": "espalda"},
    ])
    bloques = _system_con_biblioteca("INSTRUCCIONES FIJAS", ctx)

    assert len(bloques) == 2
    # Los DOS cacheados: el fijo entre clientes, el de la biblioteca entre la
    # llamada y su reintento.
    assert all(b["cache_control"] == {"type": "ephemeral"} for b in bloques)
    assert bloques[0]["text"] == "INSTRUCCIONES FIJAS"
    assert "Press banca" in bloques[1]["text"] and "\"id\": 7" in bloques[1]["text"]
    assert _biblioteca_block(ctx) == bloques[1]["text"]


def test_el_prompt_del_nucleo_ya_no_lleva_la_biblioteca_dentro():
    """Si se quedara también en el user prompt, se enviaría DOS veces."""
    from app.services.ai import generator as gen

    fuente = __import__("inspect").getsource(gen._core_user_prompt)
    assert "json.dumps(library" not in fuente
    assert "te llega arriba" in fuente
