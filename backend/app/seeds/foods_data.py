"""Base curada de composición de alimentos (hardening §2).

Valores por 100 g en CRUDO, de referencias nutricionales estándar (BEDCA/CIQUAL/
USDA como guía). No pretende ser exhaustiva: cubre los alimentos comunes de una
asesoría española para que el solver de porciones tenga con qué trabajar. Se puede
ampliar libremente; el seed es idempotente por `canonical_name`.

Formato de cada fila (dict): canonical_name, group, kcal, protein_g, carbs_g,
fat_g, fiber_g, allergens, tags, unit_grams, min_grams, max_grams, aliases.

- group: proteina | carbohidrato | grasa | verdura | fruta | lacteo | legumbre
- allergens: términos del cliente (gluten, lactosa, huevo, pescado, marisco,
  frutos secos, cacahuete, soja, sesamo).
- tags: vegano, vegetariano, sin_gluten, sin_lactosa, barato, rapido.
"""
from __future__ import annotations

_VEG = ["vegano", "vegetariano"]          # apto vegano (y por tanto vegetariano)
_VGT = ["vegetariano"]                     # vegetariano pero NO vegano


def _f(name, group, kcal, p, c, f, fiber=0.0, allergens=None, tags=None,
       unit=None, mn=0.0, mx=400.0, aliases=None) -> dict:
    return {
        "canonical_name": name, "group": group, "kcal": kcal, "protein_g": p,
        "carbs_g": c, "fat_g": f, "fiber_g": fiber, "allergens": allergens or [],
        "tags": tags or [], "unit_grams": unit, "min_grams": mn, "max_grams": mx,
        "aliases": aliases or [],
    }


FOODS: list[dict] = [
    # ---- Proteínas magras (animal) ----
    _f("Pechuga de pollo", "proteina", 120, 22.5, 0, 2.6, 0, tags=["sin_gluten", "sin_lactosa"], mn=80, mx=300, aliases=["pollo"]),
    _f("Pechuga de pavo", "proteina", 115, 22.0, 0, 2.0, 0, tags=["sin_gluten", "sin_lactosa"], mn=80, mx=300, aliases=["pavo"]),
    _f("Ternera magra", "proteina", 135, 21.5, 0, 5.0, 0, tags=["sin_gluten", "sin_lactosa"], mn=80, mx=250, aliases=["ternera", "vacuno"]),
    _f("Lomo de cerdo", "proteina", 143, 21.0, 0, 6.0, 0, tags=["sin_gluten", "sin_lactosa"], mn=80, mx=250, aliases=["cerdo", "lomo"]),
    _f("Merluza", "proteina", 90, 17.0, 0, 2.3, 0, allergens=["pescado"], tags=["sin_gluten", "sin_lactosa"], mn=100, mx=300),
    _f("Bacalao fresco", "proteina", 82, 18.0, 0, 0.7, 0, allergens=["pescado"], tags=["sin_gluten", "sin_lactosa"], mn=100, mx=300, aliases=["bacalao"]),
    _f("Salmón", "proteina", 208, 20.0, 0, 13.0, 0, allergens=["pescado"], tags=["sin_gluten", "sin_lactosa"], mn=80, mx=250, aliases=["salmon"]),
    _f("Atún al natural (lata)", "proteina", 116, 26.0, 0, 1.0, 0, allergens=["pescado"], tags=["sin_gluten", "sin_lactosa", "rapido"], mn=50, mx=200, aliases=["atun"]),
    _f("Sardina", "proteina", 172, 21.0, 0, 10.0, 0, allergens=["pescado"], tags=["sin_gluten", "sin_lactosa"], mn=60, mx=200, aliases=["sardinas"]),
    _f("Gambas", "proteina", 85, 18.0, 0.9, 1.0, 0, allergens=["marisco"], tags=["sin_gluten", "sin_lactosa"], mn=80, mx=250, aliases=["gamba", "langostino"]),
    _f("Huevo entero", "proteina", 143, 12.6, 0.7, 9.9, 0, allergens=["huevo"], tags=["vegetariano", "sin_gluten", "sin_lactosa", "barato", "rapido"], unit=55, mn=55, mx=220, aliases=["huevo", "huevos"]),
    _f("Clara de huevo", "proteina", 52, 11.0, 0.7, 0.2, 0, allergens=["huevo"], tags=["vegetariano", "sin_gluten", "sin_lactosa"], mn=30, mx=300, aliases=["claras", "clara"]),
    _f("Jamón cocido", "proteina", 107, 18.0, 1.0, 3.5, 0, tags=["sin_gluten", "sin_lactosa", "rapido"], mn=40, mx=150, aliases=["jamon york", "fiambre"]),
    _f("Jamón serrano", "proteina", 241, 31.0, 0.3, 12.0, 0, tags=["sin_gluten", "sin_lactosa"], mn=30, mx=120, aliases=["jamon"]),
    # ---- Proteínas vegetales ----
    _f("Tofu", "proteina", 144, 15.0, 2.0, 8.0, 1.0, allergens=["soja"], tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=80, mx=250),
    _f("Tempeh", "proteina", 190, 19.0, 9.0, 11.0, 4.0, allergens=["soja"], tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=60, mx=200),
    _f("Seitán", "proteina", 121, 21.0, 4.0, 2.0, 0.6, allergens=["gluten"], tags=_VEG + ["sin_lactosa"], mn=80, mx=250, aliases=["seitan"]),
    _f("Proteína de suero (whey)", "proteina", 380, 80.0, 8.0, 5.0, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten"], mn=15, mx=60, aliases=["whey", "proteina en polvo"]),
    # ---- Carbohidratos ----
    _f("Arroz blanco", "carbohidrato", 354, 7.0, 78.0, 1.0, 1.3, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=40, mx=150, aliases=["arroz"]),
    _f("Arroz integral", "carbohidrato", 350, 7.5, 73.0, 2.7, 3.5, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=40, mx=150),
    _f("Pasta", "carbohidrato", 358, 12.0, 71.0, 1.5, 3.0, allergens=["gluten"], tags=_VEG + ["barato"], mn=50, mx=150, aliases=["macarrones", "espaguetis"]),
    _f("Pan integral", "carbohidrato", 247, 9.0, 41.0, 3.5, 6.0, allergens=["gluten"], tags=_VEG + ["barato", "rapido"], unit=40, mn=30, mx=150, aliases=["pan"]),
    _f("Avena en copos", "carbohidrato", 375, 13.5, 60.0, 7.0, 10.0, allergens=["gluten"], tags=_VEG + ["barato"], mn=30, mx=120, aliases=["avena", "copos de avena"]),
    _f("Patata", "carbohidrato", 77, 2.0, 17.0, 0.1, 2.2, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=100, mx=400, aliases=["patatas"]),
    _f("Boniato", "carbohidrato", 86, 1.6, 20.0, 0.1, 3.0, tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=100, mx=350, aliases=["batata"]),
    _f("Quinoa", "carbohidrato", 368, 14.0, 64.0, 6.0, 7.0, tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=40, mx=120),
    _f("Cuscús", "carbohidrato", 376, 13.0, 77.0, 0.6, 5.0, allergens=["gluten"], tags=_VEG, mn=40, mx=120, aliases=["cuscus"]),
    _f("Pan de molde integral", "carbohidrato", 250, 9.5, 43.0, 3.5, 6.0, allergens=["gluten"], tags=_VEG + ["rapido"], unit=30, mn=30, mx=120),
    # ---- Legumbres (cocidas) ----
    _f("Lentejas cocidas", "legumbre", 116, 9.0, 20.0, 0.4, 8.0, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300, aliases=["lentejas"]),
    _f("Garbanzos cocidos", "legumbre", 139, 8.0, 22.0, 2.6, 7.6, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300, aliases=["garbanzos"]),
    _f("Alubias cocidas", "legumbre", 127, 8.5, 22.0, 0.5, 7.4, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300, aliases=["judias", "frijoles", "alubias"]),
    # ---- Grasas ----
    _f("Aceite de oliva virgen extra", "grasa", 884, 0, 0, 100.0, 0, tags=_VEG + ["sin_gluten", "sin_lactosa"], unit=10, mn=5, mx=40, aliases=["aceite", "aove"]),
    _f("Aguacate", "grasa", 160, 2.0, 9.0, 15.0, 7.0, tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=50, mx=200, aliases=["palta"]),
    _f("Almendras", "grasa", 579, 21.0, 22.0, 50.0, 12.5, allergens=["frutos secos"], tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=15, mx=60, aliases=["almendra"]),
    _f("Nueces", "grasa", 654, 15.0, 14.0, 65.0, 6.7, allergens=["frutos secos"], tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=15, mx=60, aliases=["nuez"]),
    _f("Crema de cacahuete", "grasa", 588, 25.0, 20.0, 50.0, 6.0, allergens=["cacahuete", "frutos secos"], tags=_VEG, unit=15, mn=10, mx=50, aliases=["mantequilla de cacahuete"]),
    _f("Semillas de chía", "grasa", 486, 17.0, 42.0, 31.0, 34.0, tags=_VEG + ["sin_gluten", "sin_lactosa"], unit=15, mn=10, mx=40, aliases=["chia"]),
    _f("Aceitunas", "grasa", 145, 1.0, 4.0, 15.0, 3.3, tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=20, mx=80, aliases=["olivas"]),
    # ---- Lácteos y alternativas ----
    _f("Leche desnatada", "lacteo", 35, 3.4, 5.0, 0.1, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten"], mn=100, mx=400, aliases=["leche"]),
    _f("Leche entera", "lacteo", 63, 3.2, 4.7, 3.6, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten"], mn=100, mx=400),
    _f("Yogur griego natural", "lacteo", 97, 9.0, 4.0, 5.0, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten", "rapido"], mn=100, mx=300, aliases=["yogur griego"]),
    _f("Yogur natural desnatado", "lacteo", 45, 4.5, 6.0, 0.2, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten", "rapido", "barato"], unit=125, mn=100, mx=300, aliases=["yogur"]),
    _f("Skyr", "lacteo", 63, 11.0, 4.0, 0.2, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten", "rapido"], mn=100, mx=300, aliases=["queso batido", "queso fresco batido"]),
    _f("Requesón", "lacteo", 97, 11.0, 3.0, 4.3, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten"], mn=60, mx=250, aliases=["requeson", "cottage"]),
    _f("Queso curado", "lacteo", 390, 25.0, 1.0, 32.0, 0, allergens=["lactosa"], tags=["vegetariano", "sin_gluten"], mn=20, mx=80, aliases=["queso"]),
    _f("Bebida de soja", "lacteo", 42, 3.3, 2.5, 1.8, 0.6, allergens=["soja"], tags=_VEG + ["sin_gluten", "sin_lactosa"], mn=100, mx=400, aliases=["leche de soja"]),
    _f("Bebida de avena", "lacteo", 46, 1.0, 8.0, 1.5, 0.8, allergens=["gluten"], tags=_VEG + ["sin_lactosa"], mn=100, mx=400, aliases=["leche de avena"]),
    # ---- Verduras ----
    _f("Brócoli", "verdura", 34, 2.8, 4.0, 0.4, 2.6, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300, aliases=["brocoli"]),
    _f("Espinacas", "verdura", 23, 2.9, 1.4, 0.4, 2.2, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=60, mx=300, aliases=["espinaca"]),
    _f("Calabacín", "verdura", 17, 1.2, 2.0, 0.3, 1.1, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=350, aliases=["calabacin"]),
    _f("Pimiento", "verdura", 26, 1.0, 4.6, 0.3, 1.7, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=60, mx=300, aliases=["pimientos"]),
    _f("Tomate", "verdura", 18, 0.9, 3.5, 0.2, 1.2, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=60, mx=300, aliases=["tomates"]),
    _f("Lechuga", "verdura", 15, 1.4, 1.5, 0.2, 1.3, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=40, mx=200),
    _f("Zanahoria", "verdura", 41, 0.9, 8.0, 0.2, 2.8, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=60, mx=250, aliases=["zanahorias"]),
    _f("Champiñón", "verdura", 22, 3.1, 1.0, 0.3, 1.0, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=60, mx=300, aliases=["champinon", "setas"]),
    _f("Judía verde", "verdura", 31, 1.8, 3.6, 0.2, 2.7, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300, aliases=["judia verde", "judias verdes"]),
    _f("Cebolla", "verdura", 40, 1.1, 7.6, 0.1, 1.7, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=30, mx=150),
    _f("Berenjena", "verdura", 25, 1.0, 4.5, 0.2, 3.0, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato"], mn=80, mx=300),
    # ---- Frutas ----
    _f("Plátano", "fruta", 89, 1.1, 20.0, 0.3, 2.6, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato", "rapido"], unit=120, mn=60, mx=250, aliases=["platano", "banana"]),
    _f("Manzana", "fruta", 52, 0.3, 12.0, 0.2, 2.4, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato", "rapido"], unit=150, mn=80, mx=250),
    _f("Naranja", "fruta", 47, 0.9, 9.0, 0.1, 2.4, tags=_VEG + ["sin_gluten", "sin_lactosa", "barato", "rapido"], unit=180, mn=100, mx=300),
    _f("Fresas", "fruta", 32, 0.7, 6.0, 0.3, 2.0, tags=_VEG + ["sin_gluten", "sin_lactosa", "rapido"], mn=80, mx=300, aliases=["fresa"]),
    _f("Arándanos", "fruta", 57, 0.7, 12.0, 0.3, 2.4, tags=_VEG + ["sin_gluten", "sin_lactosa", "rapido"], mn=50, mx=200, aliases=["arandanos"]),
    _f("Kiwi", "fruta", 61, 1.1, 12.0, 0.5, 3.0, tags=_VEG + ["sin_gluten", "sin_lactosa", "rapido"], unit=75, mn=60, mx=250),
    _f("Uvas", "fruta", 69, 0.7, 16.0, 0.2, 0.9, tags=_VEG + ["sin_gluten", "sin_lactosa", "rapido"], mn=60, mx=250, aliases=["uva"]),
    _f("Pera", "fruta", 57, 0.4, 12.0, 0.1, 3.1, tags=_VEG + ["sin_gluten", "sin_lactosa", "rapido"], unit=170, mn=80, mx=250),
]
