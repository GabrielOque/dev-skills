"""
Transactional email through Django's mail framework.

The provider is configuration, not code: locally the console backend prints
every email; elsewhere `EMAIL_BACKEND` / `EMAIL_*` point at any SMTP service
(or a provider backend). Subjects and templates are written in the language
the recipient reads — they reach a person without passing through the
frontend.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_templated_email(*, to, subject, template_name, context=None):
    """
    Render `template_name` with `context`, wrap it in `emails/base.html` and
    send it. Returns True when the backend accepted the message; failures are
    logged and reported as False so callers can word them for the user.
    """
    recipients = [to] if isinstance(to, str) else list(to or [])
    if not recipients or not subject:
        logger.warning("send_templated_email: missing recipients or subject")
        return False

    try:
        content = render_to_string(template_name, context or {})
        html = render_to_string(
            "emails/base.html",
            {"content": content, "subject": subject, "project_name": settings.PROJECT_NAME},
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(content).strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        message.attach_alternative(html, "text/html")
        message.send()
        return True
    except Exception:
        logger.exception("send_templated_email: could not send '%s'", template_name)
        return False
