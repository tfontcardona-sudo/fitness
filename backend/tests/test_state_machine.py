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
        period_start=date(2026, 6, 10), period_end=date(2026, 6, 23),
        period_closed=False, days_logged_in_period=5,
        last_activity_date=date(2026, 6, 14),
    )
    d = evaluate_transition(facts, TODAY)  # día 6 del período, 5 registros
    assert d.new_status is None


def test_active_becomes_at_risk_when_period_unclosed_4_days():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 5, 20), period_end=date(2026, 6, 10),
        period_closed=False, days_logged_in_period=10,
        last_activity_date=date(2026, 6, 9),
    )
    d = evaluate_transition(facts, TODAY)  # 5 días pasados del fin
    assert d.new_status == "at_risk"
    assert "sin cerrar" in d.reason
    assert d.notify_coach_at_risk is True


def test_active_becomes_at_risk_low_adherence_at_day_10():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 6), period_end=date(2026, 6, 19),
        period_closed=False, days_logged_in_period=2,  # 2/10 = 20% < 30%
        last_activity_date=date(2026, 6, 8),
    )
    d = evaluate_transition(facts, TODAY)  # día 10
    assert d.new_status == "at_risk"
    assert "adherencia" in d.reason


def test_period_just_ended_not_yet_at_risk():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 5, 31), period_end=date(2026, 6, 13),
        period_closed=False, days_logged_in_period=12,
        last_activity_date=date(2026, 6, 13),
    )
    d = evaluate_transition(facts, TODAY)  # solo 2 días pasados (<4)
    assert d.new_status is None


def test_closed_period_does_not_trigger_at_risk():
    facts = ClientFacts(
        status="awaiting_feedback", has_active_period=True,
        period_start=date(2026, 5, 20), period_end=date(2026, 6, 5),
        period_closed=True, days_logged_in_period=14,
        last_activity_date=date(2026, 6, 5),
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status is None


def test_inactive_after_30_days_idle():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 4, 1), period_end=date(2026, 4, 14),
        period_closed=False, days_logged_in_period=3,
        last_activity_date=date(2026, 5, 10),  # 36 días atrás
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status == "inactive"
    assert "sin actividad" in d.reason


def test_reminder_at_day_12_without_logs():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 4), period_end=date(2026, 6, 17),
        period_closed=False, days_logged_in_period=4,  # 4/12=33% (no at_risk) pero <6
        last_activity_date=date(2026, 6, 9),
    )
    d = evaluate_transition(facts, TODAY)  # día 12
    assert d.new_status is None
    assert d.send_reminder is True


def test_no_reminder_at_day_12_if_logging_well():
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 6, 4), period_end=date(2026, 6, 17),
        period_closed=False, days_logged_in_period=10,  # registra bien
        last_activity_date=date(2026, 6, 14),
    )
    d = evaluate_transition(facts, TODAY)  # día 12
    assert d.send_reminder is False


def test_inactivity_takes_priority_over_at_risk():
    # período sin cerrar Y 40 días idle → gana inactive
    facts = ClientFacts(
        status="active", has_active_period=True,
        period_start=date(2026, 4, 1), period_end=date(2026, 4, 14),
        period_closed=False, days_logged_in_period=1,
        last_activity_date=date(2026, 5, 5),  # 41 días
    )
    d = evaluate_transition(facts, TODAY)
    assert d.new_status == "inactive"


# ---------------------------------------------------- validez transiciones ----

def test_valid_transitions():
    assert can_transition("onboarding", "active")
    assert can_transition("active", "at_risk")
    assert can_transition("awaiting_feedback", "review_pending")
    assert can_transition("review_pending", "active")
    assert can_transition("inactive", "active")


def test_invalid_transitions():
    assert not can_transition("onboarding", "review_pending")
    assert not can_transition("inactive", "at_risk")
    assert not can_transition("review_pending", "onboarding")


# ------------------------------------------------------------ plantillas ----

BRAND = Brand(name="DQ Coaching", color_primary="#6EE7B7", color_bg="#0A0A0F",
              contact_email="david@example.com")


def test_template_plan_published_welcome():
    subject, html = plan_published(BRAND, "Marta", "https://x/p/tok", is_new_month=False)
    assert "Bienvenido" in subject
    assert "Marta" in html and "Abrir mi portal" in html and "DQ Coaching" in html


def test_template_plan_published_new_month():
    subject, html = plan_published(BRAND, "Marta", "https://x/p/tok", is_new_month=True)
    assert "nuevo plan" in subject.lower()


def test_template_reminder_includes_days_left():
    subject, html = reminder_no_logs(BRAND, "Carlos", "https://x/p/tok", days_left=3)
    assert "3 días" in html


def test_template_coach_alerts():
    s1, h1 = coach_at_risk(BRAND, "Carlos Ruiz", "5 días sin cerrar", "https://x/clients/1")
    assert "at_risk" in h1 and "Carlos Ruiz" in s1
    s2, h2 = coach_change_request(BRAND, "Marta López", "No puedo hacer sentadilla", "https://x/clients/2")
    assert "ajuste" in s2.lower() and "sentadilla" in h2
