"""
The plumbing every list endpoint shares.

Listings that need joins, computed columns or counts are written in raw SQL
(fast under real data volumes): one round trip returns the page and its
total (`COUNT(*) OVER() AS total_rows`). The SQL itself stays in each
viewset — it is the part that differs; everything around it lives here.

Envelope of every paginated listing:

    {"results": [...], "page": 1, "page_size": 10, "total_pages": 3, "total_rows": 27}
"""

import json
import logging
import math
import uuid

from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 10
# The sizes the UI offers. Anything else falls back to the default.
ALLOWED_PAGE_SIZES = (10, 25, 50, 100)

OPTIONS_DEFAULT_LIMIT = 10
OPTIONS_MAX_LIMIT = 50

# The UI's "status" filter is `archived`, inverted.
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"


def resolve_page(raw):
    """Pages are 1-based; anything invalid or lower is the first page."""
    try:
        return max(int(raw), 1)
    except (TypeError, ValueError):
        return 1


def resolve_page_size(raw):
    try:
        page_size = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return page_size if page_size in ALLOWED_PAGE_SIZES else DEFAULT_PAGE_SIZE


def resolve_options_limit(raw):
    """Clamp the `limit` of a selector (`options/`) endpoint."""
    try:
        return min(max(int(raw), 1), OPTIONS_MAX_LIMIT)
    except (TypeError, ValueError):
        return OPTIONS_DEFAULT_LIMIT


def resolve_archived_filter(statuses):
    """
    Turn `status[]=active|inactive` into a value for the `archived` column.
    Both or neither constrain nothing. Returns the string
    `build_where_clause` expects, or None to skip the filter (a string, not a
    bool: that helper drops falsy values and `False` matters here).
    """
    wants_active = STATUS_ACTIVE in statuses
    wants_inactive = STATUS_INACTIVE in statuses
    if wants_active == wants_inactive:
        return None
    return "false" if wants_active else "true"


def parse_uuid_list(values):
    """
    `= ANY(%s)` types its array from the elements, so a UUID column needs
    `uuid.UUID` objects, not strings. Invalid ids are dropped: they can match
    nothing anyway.
    """
    parsed = []
    for value in values or []:
        try:
            parsed.append(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return parsed


def fetch_page(query, params):
    """Runs a listing query and returns `(rows, total_rows)`; each row is a
    dict without the `total_rows` column."""
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    total_rows = rows[0]["total_rows"] if rows else 0
    for row in rows:
        row.pop("total_rows", None)
    return rows, total_rows


def page_response(rows, total_rows, page, page_size):
    return Response(
        {
            "results": rows,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total_rows / page_size) if page_size else 0,
            "total_rows": total_rows,
        }
    )


def error_response(code, message, exc=None, http_status=status.HTTP_400_BAD_REQUEST):
    """
    A stable `code` + English `message`. The exception is logged; its text
    only travels in `detail` when DEBUG is on, so internals never leak.
    """
    body = {"code": code, "message": message}
    if exc is not None:
        logger.exception("%s: %s", code, message)
        if settings.DEBUG:
            body["detail"] = str(exc)
    return Response(body, status=http_status)


def decode_jsonb(row, *fields):
    """A raw cursor returns jsonb as text (the ORM is what decodes it)."""
    for field in fields:
        if isinstance(row.get(field), str):
            row[field] = json.loads(row[field])
    return row
