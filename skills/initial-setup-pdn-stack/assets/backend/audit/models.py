from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from common.models import BaseModel


class AuditLog(BaseModel):
    """
    One row per state-changing API call, written by
    `common.decorators.audit_action`. Rejected and failed calls are recorded
    too: an attempted change is as visible as a successful one. Payloads are
    stored redacted (no passwords, tokens or file contents).

    Write-only from the application's point of view: there is no API route,
    and the admin is read-only.
    """

    endpoint = models.CharField(max_length=500, verbose_name="Endpoint")
    method = models.CharField(max_length=10, verbose_name="HTTP method")
    status_code = models.PositiveSmallIntegerField(verbose_name="Status code")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP address")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    django_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Django user",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        related_name="audit_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Organization",
    )
    payload = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    response = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    def __str__(self):
        who = self.django_user.username if self.django_user else "anonymous"
        return f"{who} {self.method} {self.endpoint} -> {self.status_code}"

    class Meta:
        db_table = "audit_log"
        verbose_name = "Audit log"
        verbose_name_plural = "Audit logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="audit_log_org_created_idx"),
        ]
