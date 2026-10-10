"""
View decorators. Import them from here:

    from common.decorators import audit_action, required_perms

Order on every mutating action — audit outermost, then the permission gate,
then the transaction, then DRF's `@action`:

    @audit_action
    @required_perms(["module.resource.create"])
    @transaction.atomic
    @action(detail=False, methods=["post"])
    def something(self, request): ...

The audit sees the final outcome (a 403 included) and writes outside the
view's transaction; the permission check sits above the transaction so a
denial never opens one.
"""

from .audit import audit_action
from .permissions import (
    get_effective_permission_codenames,
    required_any_perms,
    required_perms,
)

__all__ = [
    "audit_action",
    "get_effective_permission_codenames",
    "required_any_perms",
    "required_perms",
]
