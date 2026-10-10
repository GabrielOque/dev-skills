import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Abstract base for every domain model in the project.

    - `id`: UUID primary key. Non-sequential, not guessable, safe to expose in
      URLs and to generate outside the database. Every table uses one,
      including the login model (`accounts.DjangoUser`).
    - `created_at` / `updated_at`: audit timestamps.
    - `archived`: soft delete. Records are deactivated, never deleted, so
      foreign keys and history stay intact. See
      `common.viewsets.SecureModelViewSet.destroy` / `restore`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    class Meta:
        abstract = True
