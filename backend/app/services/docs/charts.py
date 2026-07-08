"""Generación de gráficas matplotlib con colores de marca (H.4).

Cada función devuelve PNG en bytes (BytesIO), listo para incrustar en el
documento Word. Usa el backend 'Agg' (sin display) y un estilo limpio acorde
al tema claro de los documentos. El color de acento es el de la marca.

Los datos vienen ya calculados por services/metrics.py (la IA nunca calcula):
estas funciones solo dibujan.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# Estilo base para documentos (tema claro, premium)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.edgecolor": "#D8D8DE",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#EEEEF2",
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": "#6B6B76",
    "ytick.color": "#6B6B76",
    "text.color": "#1A1A24",
    "axes.labelcolor": "#1A1A24",
})


def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def weight_trend_chart(
    points: list[tuple[str, float]], goal_kg: float | None, accent: str
) -> bytes:
    """Peso a lo largo del período con línea de tendencia y objetivo."""
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = [p[0] for p in points]
    values = [p[1] for p in points]
    xs = list(range(len(values)))

    ax.plot(xs, values, color=accent, linewidth=2.4, marker="o",
            markersize=5, markerfacecolor="white", markeredgecolor=accent,
            markeredgewidth=1.8, zorder=3, label="Peso")

    # Tendencia (regresión lineal simple) si hay ≥2 puntos
    if len(values) >= 2:
        n = len(values)
        mx = sum(xs) / n
        my = sum(values) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom:
            slope = sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom
            intercept = my - slope * mx
            trend = [slope * x + intercept for x in xs]
            ax.plot(xs, trend, color="#9A9AA6", linewidth=1.4, linestyle="--",
                    zorder=2, label="Tendencia")

    if goal_kg is not None:
        ax.axhline(goal_kg, color=accent, linewidth=1.2, linestyle=":",
                   alpha=0.6, zorder=1)
        ax.text(xs[-1], goal_kg, "  objetivo", va="center", fontsize=9,
                color=accent, alpha=0.8)

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("kg")
    ax.legend(frameon=False, fontsize=9, loc="best")
    return _fig_to_png(fig)


def adherence_chart(diet_pct: float, training_pct: float, accent: str) -> bytes:
    """Barras horizontales de adherencia: DIETA vs REGISTRO (0–100%).

    La segunda barra es el ratio de REGISTRO (días con diario / días del período),
    no una adherencia de entreno real: se etiqueta "Registro" para no engañar (el
    caller pasa `log_ratio`)."""
    fig, ax = plt.subplots(figsize=(6.4, 2.0))
    cats = ["Registro", "Dieta"]
    vals = [training_pct, diet_pct]
    bars = ax.barh(cats, vals, color=[accent, "#8B9DF7"], height=0.55, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% de adherencia")
    for bar, v in zip(bars, vals):
        ax.text(min(v + 2, 96), bar.get_y() + bar.get_height() / 2,
                f"{v:.0f}%", va="center", fontsize=10, fontweight="bold",
                color="#1A1A24")
    ax.grid(axis="y", visible=False)
    return _fig_to_png(fig)


def e1rm_chart(exercises: list[dict], accent: str) -> bytes:
    """Barras de e1RM por ejercicio (3–5 principales) con valor encima.

    `exercises`: [{name, e1rm_kg, delta_kg}] ya ordenados.
    """
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    names = [e["name"] for e in exercises]
    vals = [e["e1rm_kg"] for e in exercises]
    bars = ax.bar(names, vals, color=accent, width=0.6, zorder=3)
    ax.set_ylabel("e1RM (kg)")
    for bar, e in zip(bars, exercises):
        label = f"{e['e1rm_kg']:.0f}"
        if e.get("delta_kg"):
            sign = "+" if e["delta_kg"] > 0 else ""
            label += f"\n{sign}{e['delta_kg']:.1f}"
        ax.text(bar.get_x() + bar.get_width() / 2, e["e1rm_kg"],
                label, ha="center", va="bottom", fontsize=9,
                color="#1A1A24", fontweight="bold")
    ax.margins(y=0.18)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=9)
    return _fig_to_png(fig)


def perimeters_chart(
    perimeters: dict[str, list[tuple[str, float]]], accent: str
) -> bytes:
    """Evolución de perímetros (cintura, cadera…) a lo largo de los cierres."""
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    palette = [accent, "#8B9DF7", "#F7C96E", "#C99EF7"]
    for i, (name, series) in enumerate(perimeters.items()):
        xs = list(range(len(series)))
        ys = [v for _, v in series]
        ax.plot(xs, ys, marker="o", markersize=4, linewidth=2,
                color=palette[i % len(palette)], label=name, zorder=3)
    ax.set_ylabel("cm")
    if perimeters:
        any_series = next(iter(perimeters.values()))
        ax.set_xticks(list(range(len(any_series))))
        ax.set_xticklabels([lbl for lbl, _ in any_series], fontsize=9)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="best")
    return _fig_to_png(fig)


def volume_by_group_chart(volume: dict[str, float], accent: str) -> bytes:
    """Barras horizontales de series semanales por grupo muscular."""
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    items = sorted(volume.items(), key=lambda x: x[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(names, vals, color=accent, height=0.6, zorder=3)
    ax.set_xlabel("series / semana")
    ax.axvline(25, color="#F77E7E", linewidth=1.2, linestyle="--", alpha=0.7)
    ax.text(25, -0.6, "máx 25", color="#F77E7E", fontsize=8, ha="center")
    return _fig_to_png(fig)
