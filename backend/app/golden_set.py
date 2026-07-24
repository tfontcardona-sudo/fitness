"""Golden set de perfiles (hardening §14).

Perfiles que cubren casos límite (turno de noche, vegano con alergia, presupuesto
bajo, 2 comidas, entreno a las 6:00, lesión de hombro, mujer 55 sedentaria,
deportista 6 días, viajero, opositor sedentario, madre reciente…) y casos de
check-in (estancamiento con buena adherencia, bajada rápida, adherencia 50%, peso
plano con perímetros bajando…).

**Estado: `POR_VALIDAR = True`.** Los rangos esperados los generó el sistema; David
y Toni deben revisarlos antes de darlos por buenos. Mientras tanto sirven como
regresión de la CAPA DETERMINISTA (energía, macros, validador, motor quincenal):
la CI falla si un caso produce un bloqueante o si un número se sale de un rango
sano. NO ejercitan la generación con IA (sin clave en CI).
"""
from __future__ import annotations

POR_VALIDAR = True

# --- Perfiles de generación (anamnesis → objetivos deterministas) -------------
# sex, weight, height, age, goal, body_fat, level, training_days, activity,
# + expectativas: bracket de ajuste y signo del ajuste.
GOLDEN_GENERATION = [
    {"id": "hombre_graso_alto_perdida", "sex": "male", "weight": 100, "height": 178,
     "age": 35, "goal": "fat_loss", "body_fat": 30, "level": "beginner",
     "training_days": 3, "activity": "sedentary",
     "exp_bracket": "fat_loss/high", "exp_sign": -1},
    {"id": "hombre_magro_perdida", "sex": "male", "weight": 75, "height": 178,
     "age": 28, "goal": "fat_loss", "body_fat": 12, "level": "advanced",
     "training_days": 5, "activity": "active",
     "exp_bracket": "fat_loss/low", "exp_sign": -1},
    {"id": "mujer_55_sedentaria_perdida", "sex": "female", "weight": 72, "height": 162,
     "age": 55, "goal": "fat_loss", "body_fat": 34, "level": "beginner",
     "training_days": 2, "activity": "sedentary",
     "exp_bracket": "fat_loss/high", "exp_sign": -1},
    {"id": "mujer_recomp", "sex": "female", "weight": 60, "height": 165, "age": 30,
     "goal": "recomp", "body_fat": 26, "level": "intermediate", "training_days": 4,
     "activity": "light", "exp_bracket": "recomp/any", "exp_sign": -1},
    {"id": "novato_ganancia", "sex": "male", "weight": 65, "height": 175, "age": 22,
     "goal": "muscle_gain", "body_fat": 15, "level": "beginner", "training_days": 4,
     "activity": "light", "exp_bracket": "muscle_gain/novice", "exp_sign": 1},
    {"id": "avanzado_ganancia", "sex": "male", "weight": 85, "height": 182, "age": 30,
     "goal": "muscle_gain", "body_fat": 14, "level": "advanced", "training_days": 6,
     "activity": "active", "exp_bracket": "muscle_gain/exp", "exp_sign": 1},
    {"id": "deportista_6dias_mantenimiento", "sex": "male", "weight": 78, "height": 180,
     "age": 26, "goal": "maintenance", "body_fat": 13, "level": "advanced",
     "training_days": 6, "activity": "very_active",
     "exp_bracket": "maintenance/any", "exp_sign": 0},
    {"id": "opositor_sedentario_perdida", "sex": "male", "weight": 82, "height": 176,
     "age": 27, "goal": "fat_loss", "body_fat": 22, "level": "beginner",
     "training_days": 3, "activity": "sedentary",
     "exp_bracket": "fat_loss/medium", "exp_sign": -1},
    {"id": "madre_reciente_perdida", "sex": "female", "weight": 68, "height": 168,
     "age": 33, "goal": "fat_loss", "body_fat": 30, "level": "beginner",
     "training_days": 2, "activity": "light",
     "exp_bracket": "fat_loss/medium", "exp_sign": -1},
    {"id": "recomp_intermedio_hombre", "sex": "male", "weight": 80, "height": 178,
     "age": 29, "goal": "recomp", "body_fat": 18, "level": "intermediate",
     "training_days": 4, "activity": "light", "exp_bracket": "recomp/any", "exp_sign": -1},
    {"id": "lesion_recuperacion", "sex": "male", "weight": 84, "height": 181, "age": 31,
     "goal": "injury_recovery", "body_fat": 18, "level": "intermediate",
     "training_days": 3, "activity": "sedentary",
     "exp_bracket": "injury_recovery/any", "exp_sign": -1},
    {"id": "mujer_joven_ganancia", "sex": "female", "weight": 55, "height": 160,
     "age": 24, "goal": "muscle_gain", "body_fat": 22, "level": "beginner",
     "training_days": 4, "activity": "light",
     "exp_bracket": "muscle_gain/novice", "exp_sign": 1},
    {"id": "viajero_mantenimiento", "sex": "male", "weight": 76, "height": 179,
     "age": 40, "goal": "maintenance", "body_fat": 20, "level": "intermediate",
     "training_days": 3, "activity": "light",
     "exp_bracket": "maintenance/any", "exp_sign": 0},
    {"id": "mujer_graso_bajo_perdida", "sex": "female", "weight": 58, "height": 166,
     "age": 27, "goal": "fat_loss", "body_fat": 20, "level": "advanced",
     "training_days": 5, "activity": "active",
     "exp_bracket": "fat_loss/low", "exp_sign": -1},
    {"id": "senior_hombre_mantenimiento", "sex": "male", "weight": 80, "height": 175,
     "age": 62, "goal": "maintenance", "body_fat": 24, "level": "beginner",
     "training_days": 2, "activity": "light",
     "exp_bracket": "maintenance/any", "exp_sign": 0},
]

# --- Casos de check-in (seguimiento → decisión determinista) -------------------
# Cada uno mapea a un `action` esperado del motor quincenal (biweekly_engine).
GOLDEN_CHECKIN = [
    {"id": "estancamiento_buena_adherencia", "goal": "fat_loss", "weight": 80,
     "rate": (-0.5, -0.7), "weekly_delta_kg": -0.05, "adherence": 0.95,
     "exp_action": "adjust_kcal"},
    {"id": "bajada_demasiado_rapida", "goal": "fat_loss", "weight": 80,
     "rate": (-0.5, -0.7), "weekly_delta_kg": -1.2, "adherence": 0.95,
     "exp_action": "adjust_kcal"},
    {"id": "adherencia_50", "goal": "fat_loss", "weight": 80, "rate": (-0.5, -0.7),
     "weekly_delta_kg": -0.1, "adherence": 0.5, "exp_action": "work_adherence"},
    {"id": "peso_plano_perimetros_bajando", "goal": "recomp", "weight": 75,
     "rate": (0.0, 0.0), "weekly_delta_kg": 0.0, "adherence": 0.9,
     "perimeters": "down", "strength": "up", "exp_action": "hold"},
    {"id": "dentro_del_ritmo", "goal": "fat_loss", "weight": 80, "rate": (-0.5, -0.7),
     "weekly_delta_kg": -0.48, "adherence": 0.9, "exp_action": "hold"},
    {"id": "fatiga_roja_repetida", "goal": "fat_loss", "weight": 80, "rate": (-0.5, -0.7),
     "weekly_delta_kg": -0.5, "adherence": 0.9, "fatigue_now": 4.5, "fatigue_prev": 4.3,
     "exp_action": "diet_break"},
    {"id": "un_solo_pesaje", "goal": "fat_loss", "weight": 80, "rate": (-0.5, -0.7),
     "weekly_delta_kg": 0.0, "adherence": 0.9, "single": True,
     "exp_action": "request_data"},
    {"id": "ganancia_rapida_reduce", "goal": "muscle_gain", "weight": 70,
     "rate": (0.1, 0.25), "weekly_delta_kg": 0.6, "adherence": 0.95,
     "exp_action": "adjust_kcal"},
]
