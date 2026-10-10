# API conventions

The contract between the Django API and the Next.js frontend. Follow it for
every new endpoint so the frontend can be written against one shape.

## Contents
- [Resources and routes](#resources-and-routes)
- [Error contract](#error-contract)
- [The backend speaks English](#the-backend-speaks-english)
- [Viewset recipe](#viewset-recipe)
- [Decorator order](#decorator-order)
- [Listings](#listings)
- [Selector endpoints](#selector-endpoints)
- [Soft delete](#soft-delete)
- [Auditing](#auditing)

## Resources and routes

- Every app registers a `SimpleRouter` in its `urls.py`, included from
  `config/urls.py` under `api/`. Resource prefixes are plural kebab-case:
  `invoices/`, `invoice-lines/`.
- Standard surface of a resource: `list`, `retrieve`, `create`, `partial_update`
  (and `update` if full replacement makes sense), `destroy` (= deactivate),
  `PATCH <id>/restore/`.
- Extra actions are kebab-case verbs or nouns: `POST invoices/<id>/void/`,
  `GET invoices/options/`, `POST users/<id>/resend-invitation/`.
- Detail routes take the **UUID**, never a business number; searching by number
  is a `?search=` on the listing.
- Restrict `http_method_names` when a verb is not supported — a disallowed verb
  answers `405 METHOD_NOT_ALLOWED`.
- Singleton "my own" resources are addressed without id
  (`organization/current/`, `me/`).

## Error contract

Every non-2xx response:

```json
{"code": "SCREAMING_SNAKE_CASE", "message": "English, for developers", "detail": "optional"}
```

- `code` is stable and machine-readable; renaming one is a breaking change for
  the frontend. Reuse an existing code before inventing a near-duplicate.
- `message` is never shown to people. The frontend maps `code` → copy in
  `libs/api-messages.ts`; **a backend change that adds codes adds them there too**.
- `detail` is context: serializer field errors (`VALIDATION_ERROR`), the failing
  rule keys (`WEAK_PASSWORD`), the position of a bad line (a number), an
  exception text only when `DEBUG`.
- `common.exceptions.api_exception_handler` normalizes DRF errors:
  `VALIDATION_ERROR` (400), `MALFORMED_REQUEST` (400), `AUTHENTICATION_REQUIRED` /
  `TOKEN_INVALID` (401), `PERMISSION_DENIED` (403), `NOT_FOUND` (404),
  `METHOD_NOT_ALLOWED` (405), `TOO_MANY_REQUESTS` (429). A body that already has
  an uppercase `code` passes through untouched.
- Business refusals: `raise ServiceError("INVOICE_ALREADY_VOID", "The invoice is already void", 409)`
  from services, or return `Response({"code": …, "message": …}, status=…)` from views.
- Status codes: 400 invalid input or rule broken · 401 no/invalid session ·
  403 not allowed · 404 not found or not yours · 409 conflict (unique clash,
  state conflict) · 429 throttled · 503 an external dependency (email) failed.
- Unique clashes: `UniqueConflictMixin` with `conflict_code = "<ENTITY>_<FIELD>_TAKEN"`
  (`ROLE_NAME_TAKEN`) → 409.

## The backend speaks English

Code, comments, docstrings and API `message`s are English. A spec written in
another language is translated into correct English identifiers (`encargado` →
`manager`). Exceptions, because a person reads them without passing through the
frontend: email subjects and templates, permission `description`s, and
`TextChoices` labels (the API sends the value, not the label).

## Viewset recipe

```python
PERM_VIEW = "billing.invoices.view"
PERM_CREATE = "billing.invoices.create"
PERM_EDIT = "billing.invoices.edit"
PERM_DEACTIVATE = "billing.invoices.deactivate"


class InvoiceViewSet(UniqueConflictMixin, OrganizationScopedMixin, SecureModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    scope_select_related = ("customer",)
    conflict_code = "INVOICE_NUMBER_TAKEN"
    conflict_message = "An invoice with that number already exists"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(organization=get_organization(self.request))

    @required_perms([PERM_VIEW])
    def list(self, request): ...                      # raw SQL, see Listings

    @required_perms([PERM_VIEW])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_CREATE])
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_EDIT])
    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @audit_action
    @required_perms([PERM_DEACTIVATE])
    @action(detail=True, methods=["patch"])
    def restore(self, request, *args, **kwargs):
        return super().restore(request, *args, **kwargs)
```

Serializers: explicit `fields`, `read_only_fields` for ids and timestamps, no
`organization` field, `validate_<field>` strips and normalizes text, related
records by id (resolved inside the organization) or by stable codename.

Don't name a viewset method `options` (shadows the HTTP OPTIONS handler) or
`request` (shadows `self.request`): use another name and `url_path`.

## Decorator order

```
@audit_action          outermost: sees the final outcome (403 included), writes outside the transaction
@required_perms([...]) before the transaction: a denial never opens one
@transaction.atomic    only on writes
@action(...)           innermost (DRF routing metadata survives through functools.wraps)
```

## Listings

Paginated listings use raw SQL — one round trip returns the page and the total:

```python
LIST_QUERY = """
    SELECT i.id, i.number, i.status, i.total, i.archived, i.created_at,
           c.name AS customer_name,
           COUNT(*) OVER() AS total_rows
    FROM invoice i
    JOIN customer c ON c.id = i.customer_id
    {where}
    ORDER BY i.created_at DESC
    LIMIT %s OFFSET %s
"""

@required_perms([PERM_VIEW])
def list(self, request):
    page = resolve_page(request.GET.get("page"))
    page_size = resolve_page_size(request.GET.get("page_size"))
    _, where, params = build_where_clause([
        {"type": "equal", "value": get_organization_id(request), "fields": ["i.organization_id"]},
        {"type": "search", "value": request.GET.get("search"), "fields": ["i.number", "c.name"]},
        {"type": "array", "value": request.GET.getlist("statuses[]"), "fields": ["i.status"]},
        {"type": "boolean", "value": resolve_archived_filter(request.GET.getlist("status[]")), "fields": ["i.archived"]},
        {"type": "datetime_range", "value": (request.GET.get("from"), request.GET.get("to")), "fields": ["i.created_at"]},
    ])
    rows, total = fetch_page(LIST_QUERY.format(where=where), [*params, page_size, (page - 1) * page_size])
    return page_response(rows, total, page, page_size)
```

- Envelope: `{"results", "page", "page_size", "total_pages", "total_rows"}`.
- Query params: `page` (1-based), `page_size` (10/25/50/100), `search`,
  multi-value filters as `name[]` (`status[]=active&status[]=inactive`).
- Only values are parameters; column names come from code. `LIMIT/OFFSET` are
  parameters too. Never format request data into SQL.
- **Always** filter by organization. Search is accent- and case-insensitive
  (`unaccent … ILIKE`). UUID arrays need `parse_uuid_list`.
- Tie-break ordering so pages are stable (`ORDER BY created_at DESC, id`).
- Small, bounded, unpaginated lists (a catalogue, a parent's children) can use
  the ORM and return `{"results": [...], "total_rows": n}` or a plain list.
- jsonb columns come back as text from a raw cursor: `decode_jsonb(row, "field")`.

## Selector endpoints

A resource that other forms pick from exposes `GET <resource>/options/?search=&limit=`:
a small server-searched page (`resolve_options_limit`, max 50) with only what a
selector shows (`id`, label, a few attributes), active rows only. Gate it with
the **module's** reading permission or `required_any_perms` of the screens that
use it — picking a customer on an invoice must not require the customers screen.

## Soft delete

- `DELETE <resource>/<id>/` archives (`200 {"code": "ARCHIVED"}`); a second call
  answers `400 ALREADY_ARCHIVED`. `PATCH <id>/restore/` reactivates.
- Archived rows stay referenced and listed when the `status[]` filter asks for
  them; selectors never offer them; counts shown to users count active rows.
- Business guards (can't deactivate yourself, can't deactivate the last active
  X) are checked in `destroy` before delegating to `super()`.

## Auditing

`@audit_action` records every POST/PUT/PATCH/DELETE: endpoint (sensitive query
params redacted), method, status code (the real one, also for rejected and
failed calls), user, organization, IP, optional `X-Latitude`/`X-Longitude`
headers, redacted payload and response. It never breaks the endpoint and writes
one row per request. There is no API route for the log; the admin is read-only.
