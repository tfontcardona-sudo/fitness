"""Plantillas HTML de email con marca (G.5).

Cada plantilla es una función que recibe los datos y la marca, y devuelve
(asunto, html). El diseño es sobrio, mobile-first y aplica los colores de
brand_config. Todo el texto de cara al cliente va en castellano.

Las plantillas se mantienen como HTML inline (sin dependencias de assets
externos salvo el logo si existe) para máxima compatibilidad con clientes de
correo. El logo se referencia por URL pública si está disponible.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


def _esc(value: str | None) -> str:
    """Escapa texto para insertarlo con seguridad en el HTML del email.

    Sin esto, un nombre o un mensaje libre del cliente con `<`, `>` o `&`
    rompería el maquetado del correo."""
    return escape(value or "")


def _esc_ml(value: str | None) -> str:
    """Como _esc pero preserva los saltos de línea del texto libre convirtiéndolos
    en <br> (el HTML colapsa los `\\n`, dejando ilegible un mensaje de varias
    líneas escrito por el cliente)."""
    return _esc(value).replace("\n", "<br>")


@dataclass
class Brand:
    name: str
    color_primary: str
    color_bg: str
    contact_email: str | None = None
    logo_url: str | None = None


def _shell(brand: Brand, title: str, body_html: str, cta_url: str | None = None,
           cta_label: str | None = None) -> str:
    """Envoltorio común: cabecera con marca, cuerpo, CTA opcional y pie."""
    logo = (
        f'<img src="{brand.logo_url}" alt="{brand.name}" '
        f'style="max-height:48px;margin-bottom:8px">'
        if brand.logo_url else
        f'<div style="font-size:20px;font-weight:700;color:{brand.color_primary}">'
        f'{brand.name}</div>'
    )
    cta = ""
    if cta_url and cta_label:
        cta = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="margin:24px 0"><tr><td style="border-radius:10px;'
            f'background:{brand.color_primary}">'
            f'<a href="{cta_url}" style="display:inline-block;padding:13px 26px;'
            f'font-weight:600;color:#0A0A0F;text-decoration:none;border-radius:10px">'
            f'{cta_label}</a></td></tr></table>'
        )
    footer_contact = (
        f'<br>¿Dudas? Escríbenos a <a href="mailto:{brand.contact_email}" '
        f'style="color:{brand.color_primary}">{brand.contact_email}</a>.'
        if brand.contact_email else ""
    )
    return f"""\
<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f7;font-family:Inter,Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:24px 12px">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="padding:28px 28px 0">{logo}</td></tr>
<tr><td style="padding:8px 28px 28px;color:#1a1a24;font-size:15px;line-height:1.6">
<h1 style="font-size:19px;margin:12px 0 4px;color:#1a1a24">{title}</h1>
{body_html}
{cta}
<p style="font-size:13px;color:#8a8a94;margin-top:24px">
Este mensaje es parte de tu asesoría personalizada con {brand.name}.{footer_contact}
</p>
</td></tr></table></td></tr></table></body></html>"""


# ---------------------------------------------------------- al cliente ----

def portal_access(brand: Brand, first_name: str, login_url: str,
                  username: str, password: str, has_training: bool = True) -> tuple[str, str]:
    """Email de bienvenida con el acceso personal al portal (usuario y clave)."""
    from html import escape
    first_name, username, password = escape(first_name), escape(username), escape(password)
    registras = "tus entrenamientos, tu diario y tu revisión quincenal" if has_training else "tu diario y tu revisión quincenal"
    progreso = "peso, fuerza, medidas y fotos" if has_training else "peso, medidas y fotos"
    subject = f"Tu acceso personal a tu portal · {brand.name}"
    box = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%" '
        f'style="margin:18px 0;border:1px solid #e6e6ee;border-radius:12px;background:#faf9fc">'
        f'<tr><td style="padding:16px 18px;font-size:15px;color:#1a1a24">'
        f'<div style="font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#8a8a94">Usuario</div>'
        f'<div style="font-weight:700;margin:2px 0 12px">{username}</div>'
        f'<div style="font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#8a8a94">Contraseña</div>'
        f'<div style="font-weight:700;font-family:monospace;font-size:17px;letter-spacing:1px">{password}</div>'
        f'</td></tr></table>'
    )
    body = (
        f"<p>Hola {first_name}, ¡bienvenido/a! Ya tienes tu <strong>portal personal</strong>, "
        f"el sitio donde vas a llevar tu día a día con {brand.name}.</p>"
        f"<p>Desde el portal registras {registras}, y ves <strong>tu progreso</strong> "
        f"({progreso}). Es tuyo y es privado: entra con estos datos.</p>"
        f"{box}"
        f"<p style=\"font-size:13px;color:#8a8a94\">Al entrar puedes marcar "
        f"<em>«Recordarme»</em> para no tener que escribirlos cada vez. Guarda este correo "
        f"por si acaso.</p>"
    )
    return subject, _shell(brand, "Tu portal ya está listo", body, login_url, "Entrar a mi portal")


def onboarding_pay_anamnesis(brand: Brand, first_name: str, plan_label: str,
                             pay_url: str, anamnesis_url: str) -> tuple[str, str]:
    """Mensaje de arranque (email): pagar el plan + descargar/rellenar/subir la
    anamnesis (PDF editable, página pública /anamnesis/{token}), con la
    instrucción EN MAYÚSCULAS de enviarla completa."""
    first_name = _esc(first_name)
    plan_label = _esc(plan_label)
    subject = f"Tus primeros pasos con {brand.name}"
    pay_btn = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:16px 0">'
        f'<tr><td style="border-radius:10px;background:{brand.color_primary}">'
        f'<a href="{pay_url}" style="display:inline-block;padding:13px 26px;font-weight:600;'
        f'color:#0A0A0F;text-decoration:none;border-radius:10px">Pagar mi plan ({plan_label})</a>'
        f'</td></tr></table>'
    )
    anamnesis_btn = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:16px 0">'
        f'<tr><td style="border-radius:10px;background:{brand.color_secondary}">'
        f'<a href="{anamnesis_url}" style="display:inline-block;padding:13px 26px;font-weight:600;'
        f'color:#FFFFFF;text-decoration:none;border-radius:10px">Rellenar mi anamnesis</a>'
        f'</td></tr></table>'
    )
    body = (
        f"<p>Hola {first_name}, ¡bienvenido/a! Para empezar tu asesoría con "
        f"{brand.name} necesito dos cosas:</p>"
        f"<p><strong>1) Realiza el pago de tu plan {plan_label}:</strong></p>"
        f"{pay_btn}"
        f"<p><strong>2) Descarga tu cuestionario inicial (anamnesis), réllenalo "
        f"y súbelo desde este enlace:</strong></p>"
        f"{anamnesis_btn}"
        f"<p>En esa página puedes descargar el PDF editable, rellenarlo con calma "
        f"desde el móvil o el ordenador y subirlo cuando lo tengas.</p>"
        f'<p style="background:#fff7e6;border-radius:10px;padding:12px 14px;font-weight:700">'
        f"IMPORTANTE: RELLENA Y ENVÍAME TU ANAMNESIS COMPLETA PARA QUE PUEDA PREPARARTE EL PLAN.</p>"
    )
    return subject, _shell(brand, "Empecemos", body)


def plan_published(brand: Brand, first_name: str, portal_url: str, is_new_month: bool,
                   has_training: bool = True) -> tuple[str, str]:
    first_name = _esc(first_name)
    if is_new_month:
        subject = f"Tu nuevo plan del mes ya está listo · {brand.name}"
        intro = (
            f"Hola {first_name}, hemos preparado tu plan para el nuevo mes a partir de "
            "tus resultados y tu feedback. Encontrarás los ajustes en tu portal."
        )
    else:
        que = "de nutrición y entrenamiento" if has_training else "de nutrición"
        subject = f"¡Bienvenido/a! Tu plan ya está disponible · {brand.name}"
        intro = (
            f"Hola {first_name}, tu planificación personalizada {que} ya está lista. "
            "Entra en tu portal para verla y registrar tu día a día."
        )
    body = f"<p>{intro}</p>"
    return subject, _shell(brand, "Tu plan está listo", body, portal_url, "Abrir mi portal")


def reminder_no_logs(brand: Brand, first_name: str, portal_url: str, days_left: int,
                     has_training: bool = True) -> tuple[str, str]:
    first_name = _esc(first_name)
    subject = f"Un recordatorio rápido de tu seguimiento · {brand.name}"
    que = "tu peso, entrenos y adherencia" if has_training else "tu peso y adherencia"
    body = (
        f"<p>Hola {first_name}, hemos visto que llevas unos días sin registrar tu "
        f"seguimiento. Quedan <strong>{days_left} días</strong> para cerrar este "
        f"período.</p><p>Registrar {que} nos permite ajustar "
        "tu plan con precisión. ¡Solo te lleva un minuto al día!</p>"
    )
    return subject, _shell(brand, "¿Cómo va tu seguimiento?", body, portal_url, "Registrar ahora")


def closing_due(brand: Brand, first_name: str, portal_url: str, period_index: int) -> tuple[str, str]:
    first_name = _esc(first_name)
    subject = f"Es momento de cerrar tu período · {brand.name}"
    body = (
        f"<p>Hola {first_name}, tu período actual ha llegado a su fin. Para preparar "
        "tu siguiente fase necesitamos que completes el <strong>cierre</strong>: peso "
        "final, medidas opcionales, alguna foto y cómo te ha ido.</p>"
        "<p>Con esa información ajustaremos tu plan para que sigas progresando.</p>"
    )
    return subject, _shell(brand, "Cierra tu período", body, f"{portal_url}/cierre", "Completar cierre")


def video_call_scheduled(brand: Brand, first_name: str, when_label: str,
                         meet_url: str, duration_min: int) -> tuple[str, str]:
    """Confirmación de la videollamada de revisión agendada (con enlace de Meet)."""
    first_name = _esc(first_name)
    when = _esc(when_label)
    subject = f"Tu videollamada de revisión: {when_label} · {brand.name}"
    body = (
        f"<p>Hola {first_name}, ya tenemos fecha para tu <strong>videollamada de "
        f"revisión</strong>:</p>"
        f"<p style='font-size:18px'><strong>{when}</strong> "
        f"<span style='color:#6b7280'>({duration_min} min)</span></p>"
        "<p>Recibirás también una invitación en tu Google Calendar con recordatorios "
        "automáticos. Cuando llegue el momento, únete desde este mismo enlace:</p>"
        f"<p style='color:#6b7280;font-size:13px'>Enlace de Meet: "
        f"<a href='{_esc(meet_url)}' style='color:{brand.color_primary}'>{_esc(meet_url)}</a></p>"
    )
    return subject, _shell(brand, "Videollamada agendada", body, meet_url, "Unirme a la videollamada")


def video_call_reminder(brand: Brand, first_name: str, when_label: str,
                        meet_url: str) -> tuple[str, str]:
    """Recordatorio (día antes) de la videollamada, con el enlace de Meet."""
    first_name = _esc(first_name)
    when = _esc(when_label)
    subject = f"Recordatorio: videollamada {when_label} · {brand.name}"
    body = (
        f"<p>Hola {first_name}, te recuerdo que <strong>mañana</strong> tenemos tu "
        f"videollamada de revisión:</p>"
        f"<p style='font-size:18px'><strong>{when}</strong></p>"
        "<p>Nos vemos en la llamada. Puedes unirte desde el botón de abajo.</p>"
    )
    return subject, _shell(brand, "Tu videollamada es mañana", body, meet_url, "Unirme a la videollamada")


def feedback_ready(brand: Brand, first_name: str, portal_url: str,
                   has_training: bool = True) -> tuple[str, str]:
    first_name = _esc(first_name)
    subject = f"Tu informe de progreso está listo · {brand.name}"
    graficas = ("tus gráficas de progreso, evolución de fuerza y los cambios"
                if has_training else "tus gráficas de progreso y los cambios")
    body = (
        f"<p>Hola {first_name}, ya tienes tu informe de seguimiento con {graficas} "
        "que hemos hecho en tu plan (y por qué).</p>"
    )
    return subject, _shell(brand, "Tu progreso, en detalle", body, f"{portal_url}/feedback", "Ver mi informe")


def plan_republished(brand: Brand, first_name: str, portal_url: str, change_summary: str) -> tuple[str, str]:
    subject = f"Tu planificación se ha actualizado · {brand.name}"
    body = (
        f"<p>Hola {_esc(first_name)}, hemos actualizado tu planificación:</p>"
        f"<p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>{_esc_ml(change_summary)}</p>"
        "<p>Ya puedes ver los cambios en tu portal.</p>"
    )
    return subject, _shell(brand, "Plan actualizado", body, portal_url, "Ver cambios")


def plan_delivery(brand: Brand, first_name: str, portal_url: str,
                  is_adapted: bool, attached: bool) -> tuple[str, str]:
    """Entrega de la planificación por EMAIL (paquetes Start/Full). El PDF va
    adjunto si `attached`; en cualquier caso se enlaza el portal de seguimiento."""
    first_name = _esc(first_name)
    if is_adapted:
        subject = f"Tu planificación actualizada · {brand.name}"
        intro = (
            f"Hola {first_name}, he actualizado tu planificación tras tu última "
            "revisión. Tienes los cambios y su porqué detallados en el documento."
        )
    else:
        subject = f"Tu nueva planificación · {brand.name}"
        intro = (
            f"Hola {first_name}, aquí tienes tu planificación personalizada. "
            "Revísala con calma antes de empezar."
        )
    pdf_line = (
        "<p>Te adjunto tu plan en <strong>PDF</strong> para que lo tengas siempre a mano.</p>"
        if attached else ""
    )
    body = (
        f"<p>{intro}</p>{pdf_line}"
        "<p>Desde tu portal registras tu día a día (peso, diario y revisión "
        "quincenal) y ves tu progreso.</p>"
    )
    return subject, _shell(brand, "Tu plan está listo", body, portal_url, "Abrir mi portal")


def plan_manual_update(brand: Brand, first_name: str, items: list[str],
                       portal_url: str, attached: bool) -> tuple[str, str]:
    """Aviso de AJUSTE MANUAL del plan: el coach retocó la planificación y el
    mensaje EXPLICA exactamente qué cambió (lista del diff detectado)."""
    first_name = _esc(first_name)
    subject = f"He ajustado tu planificación · {brand.name}"
    lis = "".join(f'<li style="margin:4px 0">{_esc(i)}</li>' for i in items)
    pdf_line = (
        "<p>Te adjunto tu plan en <strong>PDF</strong> ya actualizado.</p>"
        if attached else ""
    )
    body = (
        f"<p>Hola {first_name}, he hecho unos ajustes en tu planificación para "
        "que siga siendo la óptima para ti. En concreto:</p>"
        f'<ul style="padding-left:18px">{lis}</ul>'
        f"{pdf_line}"
        "<p>El resto se mantiene igual. Cualquier duda, escríbeme.</p>"
    )
    return subject, _shell(brand, "Planificación ajustada", body, portal_url, "Abrir mi portal")


def feedback_delivery(brand: Brand, first_name: str, content: dict) -> tuple[str, str]:
    """Entrega del feedback quincenal por EMAIL (paquetes Start/Full): el informe
    completo (análisis, cambios, respuestas y objetivos) va en el propio correo."""
    first_name = _esc(first_name)
    subject = f"Tu feedback de la revisión quincenal · {brand.name}"
    parts: list[str] = [f"<p>Hola {first_name}, aquí tienes el feedback de estas dos semanas.</p>"]

    def _section(title: str, inner: str) -> str:
        return (
            f'<h2 style="font-size:15px;margin:20px 0 6px;color:#1a1a24">{_esc(title)}</h2>{inner}'
        )

    def _bullets(items: list) -> str:
        lis = "".join(f"<li>{_esc(str(i))}</li>" for i in items if str(i).strip())
        return f'<ul style="margin:4px 0;padding-left:20px">{lis}</ul>' if lis else ""

    if content.get("natural_analysis"):
        parts.append(f"<p>{_esc_ml(content['natural_analysis'])}</p>")
    if content.get("changes_bullets"):
        parts.append(_section("Cambios en el plan", _bullets(content["changes_bullets"])))
    if content.get("answers"):
        parts.append(_section("Respuesta a tus dudas", f"<p>{_esc_ml(content['answers'])}</p>"))
    if content.get("next_objectives"):
        parts.append(_section("Objetivos próximas 2 semanas", _bullets(content["next_objectives"])))
    if content.get("closing_message"):
        parts.append(f"<p style='font-style:italic;color:#555'>{_esc_ml(content['closing_message'])}</p>")

    return subject, _shell(brand, "Tu progreso, en detalle", "".join(parts))


def test_email(brand: Brand) -> tuple[str, str]:
    """Correo de PRUEBA para verificar que el SMTP entrega de verdad."""
    subject = f"Prueba de correo · {brand.name}"
    body = (
        "<p>Si estás leyendo esto, el envío de correo de "
        f"<strong>{_esc(brand.name)}</strong> funciona correctamente.</p>"
        "<p>Los accesos al portal, planificaciones y feedbacks se entregarán "
        "por email sin problema.</p>"
    )
    return subject, _shell(brand, "Correo configurado correctamente", body)


# ------------------------------------------------------------ al coach ----

def coach_change_request(brand: Brand, client_name: str, message: str, dashboard_url: str) -> tuple[str, str]:
    name = _esc(client_name)
    subject = f"[Acción] {client_name} ha solicitado un ajuste"
    body = (
        f"<p>El cliente <strong>{name}</strong> ha enviado una solicitud de "
        f"ajuste:</p><p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>"
        f"{_esc_ml(message)}</p><p>Revísala y actualiza el plan cuando lo resuelvas (queda activo al guardar).</p>"
    )
    return subject, _shell(brand, "Solicitud de ajuste", body, dashboard_url, "Abrir panel")


def coach_at_risk(brand: Brand, client_name: str, reason: str, dashboard_url: str) -> tuple[str, str]:
    name = _esc(client_name)
    subject = f"[Aviso] {client_name} está en riesgo de abandono"
    body = (
        f"<p>El cliente <strong>{name}</strong> ha pasado a estado "
        f"<strong>at_risk</strong>:</p>"
        f"<p style='background:#fff4f4;border-radius:10px;padding:12px 14px'>{_esc_ml(reason)}</p>"
        "<p>Quizá convenga un contacto personal para recuperar la adherencia.</p>"
    )
    return subject, _shell(brand, "Cliente en riesgo", body, dashboard_url, "Abrir panel")
