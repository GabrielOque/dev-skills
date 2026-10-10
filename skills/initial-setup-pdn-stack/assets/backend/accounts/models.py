import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class DjangoUser(AbstractUser):
    """
    The login identity (settings.AUTH_USER_MODEL): username, password and the
    Django auth flags. Deliberately separate from the business profile
    (`users.User`, reachable as `django_user.profile`), which carries the
    organization, roles and permissions. Keep auth concerns here and business
    concerns on the profile.

    - UUID primary key, like every other table.
    - `username` is always the normalized (lowercased) email: people sign in
      with their email.
    - `groups` / `user_permissions` from AbstractUser are unused — access comes
      from `users.Role` and `users.User.permissions` — and are hidden from the
      admin.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Must change password",
        help_text=(
            "Set when an administrator assigns a temporary password. The "
            "password login withholds the session until the person sets a "
            "password of their own; it clears itself when they do."
        ),
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Password changed at",
    )

    def set_password(self, raw_password):
        super().set_password(raw_password)
        if raw_password is not None:
            self.password_changed_at = timezone.now()

    class Meta:
        db_table = "django_user"
        verbose_name = "Django user"
        verbose_name_plural = "Django users"


class ValidationCode(models.Model):
    """
    A single-use, expiring code bound to one login and one **purpose**.

    The purpose is part of every lookup, so a code issued for one flow can
    never be redeemed in another (an activation link cannot reset a
    password). One active code per (user, purpose): issuing a new one
    replaces the previous, which invalidates any older link.
    """

    class Purpose(models.TextChoices):
        ACTIVATION = "ACTIVATION", "Account activation"
        PASSWORD_RESET = "PASSWORD_RESET", "Password reset"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    django_user = models.ForeignKey(
        "accounts.DjangoUser",
        related_name="validation_codes",
        on_delete=models.CASCADE,
        verbose_name="Django user",
    )
    purpose = models.CharField(max_length=32, choices=Purpose.choices, verbose_name="Purpose")
    code = models.CharField(max_length=128, db_index=True, verbose_name="Code")
    expires_at = models.DateTimeField(verbose_name="Expires at")

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.django_user.username} · {self.get_purpose_display()}"

    class Meta:
        db_table = "validation_code"
        verbose_name = "Validation code"
        verbose_name_plural = "Validation codes"
        constraints = [
            models.UniqueConstraint(
                fields=["django_user", "purpose"],
                name="validation_code_unique_purpose_per_user",
            ),
        ]
