from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """
    Database-wide PostgreSQL extensions the project relies on.

    `unaccent`: `ILIKE` folds case but not diacritics, so without it "credito"
    never matches "Crédito". Every text search uses it — the ORM's
    `__unaccent__icontains` and the raw-SQL `build_where_clause` alike.

    Lives in `common` because it is infrastructure, not a feature. Needs a
    role allowed to create extensions (managed PostgreSQL services allow
    `unaccent`).
    """

    initial = True

    dependencies = []

    operations = [
        UnaccentExtension(),
    ]
