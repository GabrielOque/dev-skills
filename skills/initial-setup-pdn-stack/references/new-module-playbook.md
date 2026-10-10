# Playbook: adding a domain module

Use this after the base setup, every time the user describes a part of the
product ("we need to manage invoices", "clients book appointments"). The
example uses a fictitious `billing` module with an `Invoice`; replace every name
with the user's own domain language — **never reuse example names**.

## Contents
- [0. Model the domain with the user](#0-model-the-domain-with-the-user)
- [1. Backend app](#1-backend-app)
- [2. Permissions](#2-permissions)
- [3. Error codes](#3-error-codes)
- [4. Migrations and tests](#4-migrations-and-tests)
- [5. Frontend](#5-frontend)
- [6. Definition of done](#6-definition-of-done)

## 0. Model the domain with the user

Before writing code, agree on (in the user's words, then translated to English
identifiers):

- the module (Django app) and its resources (models), with fields, types,
  required/optional, uniqueness *within the organization*, and relations;
- each resource's lifecycle: statuses and transitions, what "deactivate" means,
  which records are immutable once confirmed;
- who does what: the actions → codenames (`<module>.<resource>.<action>`) and
  which existing roles should get them (the owner composes roles later);
- the listings: columns, filters, search fields, default order;
- numbering, files, notifications, anything external.

Show the proposed models and codenames and get a confirmation before
generating migrations.

## 1. Backend app

```bash
python manage.py startapp billing
```

Then reshape it to the app anatomy (backend-architecture.md):
`models/ serializers/ views/ services/ tests/` packages, `choices.py`, `urls.py`;
delete the generated `models.py`, `views.py`, `tests.py`. Register the app in
`INSTALLED_APPS` (after the base apps) and its urls in `config/urls.py`:
`path("api/", include("billing.urls"))`.

`billing/models/invoice.py`:

```python
from django.db import models

from common.models import BaseModel

from ..choices import InvoiceStatus


class Invoice(BaseModel):
    """What it represents and the rules a reader must know."""

    organization = models.ForeignKey(
        "organizations.Organization", related_name="invoices", on_delete=models.CASCADE,
        verbose_name="Organization",
    )
    number = models.CharField(max_length=32, verbose_name="Number")
    status = models.CharField(
        max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, verbose_name="Status",
    )
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Total")

    def __str__(self):
        return self.number

    class Meta:
        db_table = "invoice"
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "number"], name="invoice_unique_number_per_organization"),
        ]
```

`billing/models/__init__.py`: `from .invoice import Invoice` + `__all__`.

Serializer (`billing/serializers/invoice.py`): explicit fields, read-only ids
and timestamps, no `organization` field, normalization in `validate_<field>`.

Viewset (`billing/views/invoice.py`): follow the recipe in
api-conventions.md — `UniqueConflictMixin, OrganizationScopedMixin,
SecureModelViewSet`, every action decorated, raw-SQL `list`, `destroy` /
`restore` overridden, extra actions for state transitions
(`@action(detail=True, methods=["post"]) def void`) calling services.

Services (`billing/services.py`): transitions and multi-model writes in
`@transaction.atomic`, `ServiceError` for refusals.

Admin (`billing/admin.py`): `BaseModelAdmin` subclass per model.

URLs (`billing/urls.py`):

```python
router = SimpleRouter()
router.register(r"invoices", InvoiceViewSet, basename="invoices")
urlpatterns = router.urls
```

## 2. Permissions

```bash
python manage.py add_permission \
  billing.invoices.view "Ver facturas" \
  billing.invoices.create "Crear facturas" \
  billing.invoices.edit "Editar facturas en borrador" \
  billing.invoices.deactivate "Desactivar o reactivar facturas" \
  billing.invoices.void "Anular facturas emitidas"
python manage.py sync_permissions
```

Descriptions in the UI language. Then mirror them in the frontend
`libs/permission-codenames.ts`:

```ts
billing: {
  invoices: {
    view: "billing.invoices.view",
    create: "billing.invoices.create",
    edit: "billing.invoices.edit",
    deactivate: "billing.invoices.deactivate",
    void: "billing.invoices.void",
  },
},
```

Existing roles don't get new permissions automatically; tell the user to grant
them (or extend the all-permissions role by re-running `bootstrap_organization`
for the owner's organization).

## 3. Error codes

Every new `code` the module returns (`INVOICE_NUMBER_TAKEN`,
`INVOICE_ALREADY_VOID`…) gets its copy in the frontend `libs/api-messages.ts`
in the same change.

## 4. Migrations and tests

```bash
python manage.py makemigrations billing --name initial
python manage.py migrate
python manage.py test billing
```

Tests (`billing/tests/test_invoices.py`, using `common/testing.py`): allowed
with the permission, `403` without it, another organization's invoice is
`404`, the unique clash is `409 INVOICE_NUMBER_TAKEN`, each business rule of the
services, the listing's search and filters.

## 5. Frontend

```
types/invoice.ts                       Invoice interface (backend field names) + export in types/index.ts
actions/invoices.ts                    (optional) listInvoices, getInvoice, … over apiClient
app/(app)/billing/invoices/page.tsx    thin: metadata + <InvoicesPage />
app/(app)/billing/invoices/[id]/page.tsx
app/(app)/billing/invoices/new/page.tsx
page_components/invoices/
  index.ts
  invoices-page.tsx                    container: URL state, apiClient, usePermissions
  invoices-table.tsx                   presentational
  invoice-editor.tsx                   container (create / edit / read-only)
libs/permission-codenames.ts           + billing.invoices.*
libs/api-messages.ts                   + the module's codes
```

- Containers compute `can(...)` and pass booleans down; denied controls are hidden.
- Table state (page, page_size, search, filters) lives in the URL.
- Errors through `translateApiError`; control flow through `getApiCode`.
- If the project has a navigation config, add the entry with its permissions.
- Styling follows whatever design system the project chose; if none was chosen,
  keep markup semantic and unstyled and ask before introducing one.

## 6. Definition of done

- [ ] Models on `BaseModel`, tenant FK or lookup, constraints named.
- [ ] Every action gated; mutations audited; `destroy` archives.
- [ ] Codenames in the fixture (deterministic pks) and mirrored in the frontend.
- [ ] New error codes mapped in `libs/api-messages.ts`.
- [ ] Migration committed with a descriptive name; `makemigrations --check` clean.
- [ ] Backend tests green; frontend `lint`, `tsc --noEmit`, `build` green.
- [ ] New settings in `.env.example`; `CLAUDE.md` updated if a convention changed.
