"""Request-level hygiene shared by every endpoint."""


class TrimQueryParamsMiddleware:
    """
    Query-string values arrive trimmed, so «  ABC-12 » and «ABC-12» are the
    same search. Done once here so no listing or filter has to remember it —
    a search that forgets to strip silently answers "no results".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.GET:
            params = request.GET.copy()
            changed = False
            for key in list(params.keys()):
                values = params.getlist(key)
                trimmed = [value.strip() for value in values]
                if trimmed != values:
                    params.setlist(key, trimmed)
                    changed = True
            if changed:
                params._mutable = False
                request.GET = params
        return self.get_response(request)
