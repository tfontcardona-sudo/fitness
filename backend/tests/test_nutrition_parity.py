"""Test de PARIDAD del contrato de objetivos calóricos (hardening §1).

El sistema tenía la MISMA lógica de objetivos calóricos duplicada en dos
lenguajes: `app/services/nutrition_scale.py` (autoridad) y
`frontend/src/lib/nutritionTargets.ts` (editor en vivo). Dos implementaciones
= deriva garantizada (de hecho este test cazó una: 95×1,9=180,5 daba 180 g en
el backend por redondeo bancario y 181 g en el editor por Math.round).

Elimina esa deriva sin obligar a un único lenguaje (el editor necesita cálculo
local para responder al instante): fija AMBAS contra un contrato compartido de
vectores dorados (`shared/nutrition_contract.json`, generado desde el backend).
Comprueba:

  1. La implementación PYTHON reproduce el contrato (pin de regresión backend).
  2. La implementación TS, transpilada con esbuild y ejecutada con node,
     reproduce EL MISMO contrato (paridad de los primitivos puros idénticos:
     kcalOf, macrosForKcal, macrosScaledToKcal) + las constantes compartidas.
  3. Los PARÁMETROS del clamp (bounds por kg y topes de kcal) coinciden entre
     clamp_targets (backend) y clampTargets (frontend). No se comparan esas dos
     funciones vector-a-vector porque el backend reparte "acotar" + "cuadrar
     4/4/9" en dos pasos y el frontend en uno (descomposición distinta por
     diseño); se fijan sus parámetros, que es lo que puede derivar.

Si node/esbuild no están disponibles, la parte de ejecución TS se salta con
aviso (la CI del repo compila el frontend, así que allí sí corre).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from app.services.nutrition_scale import (
    FAT_PER_KG,
    MAX_DEFICIT_PCT,
    MAX_SURPLUS_PCT,
    kcal_of,
    macros_for_kcal,
    macros_scaled_to_kcal,
)

_ROOT = Path(__file__).resolve().parents[2]
_CONTRACT = _ROOT / "shared" / "nutrition_contract.json"
_FRONTEND = _ROOT / "frontend"
_TS_LIB = _FRONTEND / "src" / "lib" / "nutritionTargets.ts"


def _contract() -> dict:
    return json.loads(_CONTRACT.read_text())


def _py_run(fn: str, args: list):
    if fn == "kcalOf":
        return kcal_of(*args)
    if fn == "macrosForKcal":
        return macros_for_kcal(*args)
    if fn == "macrosScaledToKcal":
        return macros_scaled_to_kcal(*args)
    raise AssertionError(f"función desconocida en el contrato: {fn}")


def test_contrato_existe_y_constantes_coinciden_con_backend():
    c = _contract()
    assert c["cases"], "el contrato no tiene casos"
    assert c["constants"]["MAX_DEFICIT_PCT"] == MAX_DEFICIT_PCT
    assert c["constants"]["MAX_SURPLUS_PCT"] == MAX_SURPLUS_PCT
    assert c["constants"]["FAT_PER_KG"] == FAT_PER_KG


def test_backend_reproduce_el_contrato():
    """El backend (autoridad) reproduce sus propios vectores: pin de regresión —
    si alguien cambia la lógica sin regenerar el contrato, falla."""
    for case in _contract()["cases"]:
        got = _py_run(case["fn"], case["args"])
        assert got == case["expected"], (
            f"{case['fn']}{case['args']} → backend={got} contrato={case['expected']}"
        )


def _node_tools() -> tuple[str, str] | None:
    import shutil

    node = shutil.which("node")
    esbuild = _FRONTEND / "node_modules" / ".bin" / "esbuild"
    if node and esbuild.exists():
        return node, str(esbuild)
    return None


def test_frontend_reproduce_el_contrato(tmp_path):
    """La implementación TS del editor produce EXACTAMENTE lo mismo que el
    backend para cada vector. Transpila el .ts con esbuild y lo corre con node."""
    tools = _node_tools()
    if not tools:
        pytest.skip("node/esbuild no disponibles: paridad TS no verificable aquí "
                    "(sí corre en la CI que compila el frontend)")
    node, esbuild = tools

    driver = tmp_path / "driver.ts"
    driver.write_text(
        "import { kcalOf, macrosForKcal, macrosScaledToKcal, "
        "MAX_DEFICIT_PCT, MAX_SURPLUS_PCT, GOAL_RULES } from "
        f'{json.dumps(str(_TS_LIB).removesuffix(".ts"))};\n'
        'import * as fs from "fs";\n'
        "const contract = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));\n"
        "const out: any = { cases: [], constants: {} };\n"
        "for (const c of contract.cases) {\n"
        "  let r;\n"
        "  if (c.fn === 'kcalOf') r = kcalOf(c.args[0], c.args[1], c.args[2]);\n"
        "  else if (c.fn === 'macrosForKcal') r = macrosForKcal(c.args[0], c.args[1], c.args[2]);\n"
        "  else if (c.fn === 'macrosScaledToKcal') r = macrosScaledToKcal(c.args[0], c.args[1]);\n"
        "  else throw new Error('fn desconocida: ' + c.fn);\n"
        "  out.cases.push(r);\n"
        "}\n"
        "out.constants = { MAX_DEFICIT_PCT, MAX_SURPLUS_PCT,\n"
        "  FAT_PER_KG: Object.fromEntries(Object.entries(GOAL_RULES).map(([k,v]:any)=>[k,v.fatPerKg])),\n"
        "  PROTEIN_MID_PER_KG: Object.fromEntries(Object.entries(GOAL_RULES).map(([k,v]:any)=>[k,v.proteinPerKg])) };\n"
        "process.stdout.write(JSON.stringify(out));\n"
    )
    bundle = tmp_path / "bundle.cjs"
    build = subprocess.run(
        [esbuild, str(driver), "--bundle", "--platform=node",
         "--format=cjs", f"--outfile={bundle}"],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, f"esbuild falló:\n{build.stderr}"
    run = subprocess.run([node, str(bundle), str(_CONTRACT)],
                         capture_output=True, text=True)
    assert run.returncode == 0, f"node falló:\n{run.stderr}"
    ts = json.loads(run.stdout)

    contract = _contract()
    for case, ts_out in zip(contract["cases"], ts["cases"]):
        assert ts_out == case["expected"], (
            f"DERIVA {case['fn']}{case['args']}: frontend={ts_out} "
            f"backend/contrato={case['expected']} — sincroniza "
            f"nutritionTargets.ts con nutrition_scale.py"
        )
    assert ts["constants"]["MAX_DEFICIT_PCT"] == contract["constants"]["MAX_DEFICIT_PCT"]
    assert ts["constants"]["MAX_SURPLUS_PCT"] == contract["constants"]["MAX_SURPLUS_PCT"]
    assert ts["constants"]["FAT_PER_KG"] == contract["constants"]["FAT_PER_KG"]
    assert ts["constants"]["PROTEIN_MID_PER_KG"] == contract["constants"]["PROTEIN_MID_PER_KG"]


def test_bounds_del_clamp_coinciden_en_el_fuente_ts():
    """clamp_targets (backend) y clampTargets (frontend) NO se comparan
    vector-a-vector (descomposición distinta por diseño), pero sus PARÁMETROS sí
    deben coincidir: guarda de fuente que caza un cambio de bounds en el editor
    sin actualizar el backend. Los literales son estables (bounds fisiológicos)."""
    src = _TS_LIB.read_text()
    b = _contract()["constants"]["CLAMP_BOUNDS"]
    # proteína 1,2–3,0 g/kg · grasa 0,6–2,0 g/kg · suelo grasa 20 g · kcal 1100–4500
    for token in (
        f"w * {b['protein_per_kg'][0]}", f"w * {b['protein_per_kg'][1]}",
        f"w * {b['fat_per_kg'][0]}", f"w * {b['fat_per_kg'][1]}",
        str(b["fat_floor_g"]), str(b["kcal_abs"][0]), str(b["kcal_abs"][1]),
    ):
        assert token in src, (
            f"El bound del clamp «{token}» ya no está en nutritionTargets.ts: "
            f"clampTargets ha derivado de clamp_targets del backend."
        )
