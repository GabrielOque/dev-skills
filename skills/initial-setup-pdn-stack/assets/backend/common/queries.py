"""Safe WHERE-clause building for raw-SQL listings — see `build_where_clause`."""


def build_where_clause(filters):
    """
    Build a parametrized SQL WHERE clause.

    Each filter is `{"type": str, "value": any, "fields": [column, ...]}`.
    Filters whose value is empty are skipped, so optional query params can be
    passed straight through.

    Types:
        search          unaccent(col) ILIKE unaccent(%s), OR-ed across `fields`
                        (case- and accent-insensitive; needs the `unaccent`
                        extension, created by common/migrations/0001)
        equal           col = %s                     (scalar)
        array / in      col = ANY(%s)                (list)
        exclude_array   col <> ALL(%s)               (list)
        boolean         col = %s                     ("true" / "false")
        is_null         col IS NULL / IS NOT NULL    (True / False)
        in_or_null      (col = ANY(%s) OR col IS NULL)
        datetime_range  col BETWEEN %s AND %s, or an open-ended bound

    Returns `(clauses, where_sql, params)`; `where_sql` includes `WHERE`, or is
    empty when nothing applies. Column names come from code, never from the
    request — only values are parameters.

    Why ANY/ALL instead of IN: with psycopg 3 a Python tuple adapts to a
    PostgreSQL composite, not to a value list, so `IN %s` breaks. A Python
    list adapts to an array, which `= ANY(...)` takes. Arrays are typed from
    their elements: a UUID column needs `uuid.UUID` objects (see
    `common.listing.parse_uuid_list`).
    """
    params = []
    clauses = []

    for item in filters:
        kind = item.get("type")
        value = item.get("value")
        fields = item.get("fields") or []
        if not kind or not fields:
            continue
        if kind in ("is_null", "equal"):
            if value is None:
                continue
        elif not value:
            continue

        column = fields[0]

        if kind == "search":
            term = str(value).strip()
            if not term:
                continue
            likes = [f"unaccent({field}) ILIKE unaccent(%s)" for field in fields]
            clauses.append("(" + " OR ".join(likes) + ")")
            params.extend([f"%{term}%"] * len(likes))
        elif kind == "equal":
            clauses.append(f"{column} = %s")
            params.append(value)
        elif kind in ("array", "in"):
            clauses.append(f"{column} = ANY(%s)")
            params.append(list(value))
        elif kind == "exclude_array":
            clauses.append(f"{column} <> ALL(%s)")
            params.append(list(value))
        elif kind == "boolean":
            clauses.append(f"{column} = %s")
            params.append(value)
        elif kind == "is_null":
            clauses.append(f"{column} IS NULL" if value else f"{column} IS NOT NULL")
        elif kind == "in_or_null":
            clauses.append(f"({column} = ANY(%s) OR {column} IS NULL)")
            params.append(list(value))
        elif kind == "datetime_range":
            start, end = value
            if start and end:
                clauses.append(f"{column} BETWEEN %s AND %s")
                params.extend([start, end])
            elif start:
                clauses.append(f"{column} >= %s")
                params.append(start)
            elif end:
                clauses.append(f"{column} <= %s")
                params.append(end)

    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return clauses, where_sql, params
