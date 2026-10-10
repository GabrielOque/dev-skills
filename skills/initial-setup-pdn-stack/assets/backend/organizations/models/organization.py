from django.db import models
from django.utils.text import slugify

from common.models import BaseModel


class Organization(BaseModel):
    """
    The tenant. Every business record belongs to an organization, directly
    (`organization` FK) or through a parent.

    In a multi-tenant product each customer is one row. In a single-company
    product there is exactly one row — the company profile — and the same
    code works unchanged, so going multi-tenant later costs no migration.

    Kept minimal on purpose: domain-specific settings belong in their own
    app or model, not here.
    """

    name = models.CharField(max_length=255, verbose_name="Name")
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name="Slug",
        help_text="Stable identifier used in links. Generated from the name and never changed.",
    )
    email = models.EmailField(blank=True, default="", verbose_name="Contact email")
    phone = models.CharField(max_length=32, blank=True, default="", verbose_name="Contact phone")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.name)[:240] or "organization"
        slug, suffix = base, 2
        while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    def __str__(self):
        return self.name

    class Meta:
        db_table = "organization"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]
