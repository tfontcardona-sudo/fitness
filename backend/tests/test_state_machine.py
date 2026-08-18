"""Tests unitarios de la máquina de estados (G.2) y plantillas de email (G.5).

La función `evaluate_transition` es pura: estos tests fijan hechos y comprueban
la decisión, sin tocar la base de datos.
"""

from __future__ import annotations

from datetime import date

from app.services.email_templates import (
    Brand,
    coach_at_risk,
    coach_change_request,
    plan_published,
    reminder_no_logs,
)
from app.services.state_machine import (
    ClientFacts,
    TransitionDecision,
    can_transition,
    evaluate_transition,
)

TODAY = date(2026, 6, 15)


# ---------------------------------------------- transiciones por tiempo ----

def test_onboarding_does_not_transition_by_time():
    facts = ClientFacts(status="onboarding")
    d = evaluate_transition(facts, TODAY)
    assert d.new_status is None


def test_active_well_adhered_stays_active():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 10), days_logged_in_period=5,
        last_activity_date=date(2026, 6, 14),
    )
    d = evaluate_transition(facts, TODAY)  # día 6 de la ventana, 5 registros
    assert d.new_status is None


def test_active_becomes_at_risk_low_adherence_at_day_10():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 6), days_logged_in_period=2,  # 2/10 = 20% < 30%
        last_activity_date=date(2026, 6, 8),
    )
    d = evaluate_transition(facts, TODAY)  # día 10
    assert d.new_status == "at_risk"
    assert "adherencia" in d.reason
    assert d.notify_coach_at_risk is True


def test_at_risk_vuelve_a_active_al_recuperar_la_constancia():
    """Sin cierre de período, la recuperación depende SOLO de la ventana móvil:
    el cliente que retoma el registro sale de riesgo solo."""
    facts = ClientFacts(
        status="at_risk", has_active_period=True,
        period_start=date(2026, 6, 6), days_logged_in_period=8,  # 8/10 = 80%
        last_activity_date=date(2026, 6, 14),
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status == "active"
    assert "constancia recuperada" in d.reason


def test_inactive_after_30_days_idle():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 4, 1), days_logged_in_period=3,
        last_activity_date=date(2026, 5, 10),  # 36 días atrás
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status == "inactive"
    assert "sin actividad" in d.reason


def test_reminder_at_day_12_without_logs():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 4), days_logged_in_period=4,  # 4/12=33% (no at_risk) pero <6
        last_activity_date=date(2026, 6, 9),
    )
    d = evaluate_transition(facts, TODAY)  # día 12
    assert d.new_status is None
    assert d.send_reminder is True


def test_no_reminder_at_day_12_if_logging_well():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 4), days_logged_in_period=10,  # registra bien
        last_activity_date=date(2026, 6, 14),
    )
    d = evaluate_transition(facts, TODAY)  # día 12
    assert d.send_reminder is False


def test_inactivity_takes_priority_over_at_risk():
    # constancia por los suelos Y 41 días idle → gana inactive
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 4, 1), days_logged_in_period=1,
        last_activity_date=date(2026, 5, 5),  # 41 días
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status == "inactive"


# ---------------------------------------------------- validez transiciones ----

def test_valid_transitions():
    assert can_transition("onboarding", "active")
    assert can_transition("active", "at_risk")
    assert can_transition("at_risk", "active")
    assert can_transition("inactive", "active")


def test_estados_del_ciclo_quincenal_eliminados():
    # "awaiting_feedback" y "review_pending" eran del ciclo de 14 días: sin
    # cierre de período nada los asignaba y quedaban colgados.
    assert not can_transition("active", "awaiting_feedback")
    assert not can_transition("active", "review_pending")


def test_invalid_transitions():
    assert not can_transition("onboarding", "at_risk")
    assert not can_transition("inactive", "at_risk")


# ------------------------------------------------------------ plantillas ----

BRAND = Brand(name="Professional Coaching", color_primary="#6EE7B7", color_bg="#0A0A0F",
              contact_email="david@example.com")


def test_template_plan_published_welcome():
    subject, html = plan_published(BRAND, "Marta", "https://x/p/tok", is_new_month=False)
    assert "Bienvenido" in subject
    assert "Marta" in html and "Abrir mi portal" in html and "Professional Coaching" in html


def test_template_plan_published_new_month():
    subject, html = plan_published(BRAND, "Marta", "https://x/p/tok", is_new_month=True)
    assert "nuevo plan" in subject.lower()


def test_template_reminder_no_habla_de_cierre():
    """El seguimiento es continuo: el recordatorio no anuncia fecha límite."""
    subject, html = reminder_no_logs(BRAND, "Carlos", "https://x/p/tok")
    assert "Carlos" in html
    assert "cerrar este período" not in html and "días</strong> para cerrar" not in html


def test_template_coach_alerts():
    s1, h1 = coach_at_risk(BRAND, "Carlos Ruiz", "5 días sin cerrar", "https://x/clients/1")
    assert "at_risk" in h1 and "Carlos Ruiz" in s1
    s2, h2 = coach_change_request(BRAND, "Marta López", "No puedo hacer sentadilla", "https://x/clients/2")
    assert "ajuste" in s2.lower() and "sentadilla" in h2
