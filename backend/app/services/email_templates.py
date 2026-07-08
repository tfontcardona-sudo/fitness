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
                  username: str, password: str) -> tuple[str, str]:
    """Email de bienvenida con el acceso personal al portal (usuario y clave)."""
    from html import escape
    first_name, username, password = escape(first_name), escape(username), escape(password)
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
        f"<p>Desde el portal registras tus entrenamientos, tu diario y tu revisión "
        f"quincenal, y ves <strong>tu progreso</strong> (peso, fuerza, medidas y fotos). "
        f"Es tuyo y es privado: entra con estos datos.</p>"
        f"{box}"
        f"<p style=\"font-size:13px;color:#8a8a94\">Al entrar puedes marcar "
        f"<em>«Recordarme»</em> para no tener que escribirlos cada vez. Guarda este correo "
        f"por si acaso.</p>"
    )
    return subject, _shell(brand, "Tu portal ya está listo", body, login_url, "Entrar a mi portal")


def plan_published(brand: Brand, first_name: str, portal_url: str, is_new_month: bool) -> tuple[str, str]:
    if is_new_month:
        subject = f"Tu nuevo plan del mes ya está listo · {brand.name}"
        intro = (
            f"Hola {first_name}, hemos preparado tu plan para el nuevo mes a partir de "
            "tus resultados y tu feedback. Encontrarás los ajustes en tu portal."
        )
    else:
        subject = f"¡Bienvenido/a! Tu plan ya está disponible · {brand.name}"
        intro = (
            f"Hola {first_name}, tu planificación personalizada de nutrición y "
            "entrenamiento ya está lista. Entra en tu portal para verla y registrar "
            "tu día a día."
        )
    body = f"<p>{intro}</p><p>En la vista <strong>HOY</strong> verás qué comer y qué entrenar cada día, en menos de 30 segundos.</p>"
    return subject, _shell(brand, "Tu plan está listo", body, portal_url, "Abrir mi portal")


def reminder_no_logs(brand: Brand, first_name: str, portal_url: str, days_left: int) -> tuple[str, str]:
    subject = f"Un recordatorio rápido de tu seguimiento · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos visto que llevas unos días sin registrar tu "
        f"seguimiento. Quedan <strong>{days_left} días</strong> para cerrar este "
        "período.</p><p>Registrar tu peso, entrenos y adherencia nos permite ajustar "
        "tu plan con precisión. ¡Solo te lleva un minuto al día!</p>"
    )
    return subject, _shell(brand, "¿Cómo va tu seguimiento?", body, portal_url, "Registrar ahora")


def closing_due(brand: Brand, first_name: str, portal_url: str, period_index: int) -> tuple[str, str]:
    subject = f"Es momento de cerrar tu período · {brand.name}"
    body = (
        f"<p>Hola {first_name}, tu período actual ha llegado a su fin. Para preparar "
        "tu siguiente fase necesitamos que completes el <strong>cierre</strong>: peso "
        "final, medidas opcionales, alguna foto y cómo te ha ido.</p>"
        "<p>Con esa información ajustaremos tu plan para que sigas progresando.</p>"
    )
    return subject, _shell(brand, "Cierra tu período", body, f"{portal_url}/cierre", "Completar cierre")


def feedback_ready(brand: Brand, first_name: str, portal_url: str) -> tuple[str, str]:
    subject = f"Tu informe de progreso está listo · {brand.name}"
    body = (
        f"<p>Hola {first_name}, ya tienes tu informe de seguimiento con tus gráficas "
        "de progreso, evolución de fuerza y los cambios que hemos hecho en tu plan "
        "(y por qué).</p>"
    )
    return subject, _shell(brand, "Tu progreso, en detalle", body, f"{portal_url}/feedback", "Ver mi informe")


def plan_republished(brand: Brand, first_name: str, portal_url: str, change_summary: str) -> tuple[str, str]:
    subject = f"Tu planificación se ha actualizado · {brand.name}"
    body = (
        f"<p>Hola {first_name}, hemos actualizado tu planificación:</p>"
        f"<p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>{change_summary}</p>"
        "<p>Ya puedes ver los cambios en tu portal.</p>"
    )
    return subject, _shell(brand, "Plan actualizado", body, portal_url, "Ver cambios")


# ------------------------------------------------------------ al coach ----

def coach_change_request(brand: Brand, client_name: str, message: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Acción] {client_name} ha solicitado un ajuste"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha enviado una solicitud de "
        f"ajuste:</p><p style='background:#f4f4f7;border-radius:10px;padding:12px 14px'>"
        f"{message}</p><p>Revísala y actualiza el plan cuando lo resuelvas (queda activo al guardar).</p>"
    )
    return subject, _shell(brand, "Solicitud de ajuste", body, dashboard_url, "Abrir panel")


def coach_at_risk(brand: Brand, client_name: str, reason: str, dashboard_url: str) -> tuple[str, str]:
    subject = f"[Aviso] {client_name} está en riesgo de abandono"
    body = (
        f"<p>El cliente <strong>{client_name}</strong> ha pasado a estado "
        f"<strong>at_risk</strong>:</p>"
        f"<p style='background:#fff4f4;border-radius:10px;padding:12px 14px'>{reason}</p>"
        "<p>Quizá convenga un contacto personal para recuperar la adherencia.</p>"
    )
    return subject, _shell(brand, "Cliente en riesgo", body, dashboard_url, "Abrir panel")
