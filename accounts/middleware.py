from django.shortcuts import redirect

EXEMPT_PREFIXES = (
    "/tools/accounts/",
    "/accounts/",            
    "/tools/static/",              
    "/tools/media/",               
    "/favicon.ico",
    "/robots.txt",
)

class ForceGoogleLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        p = request.path
        if p.startswith("/tools/") \
           and not request.user.is_authenticated \
           and not any(p.startswith(x) for x in EXEMPT_PREFIXES):
            return redirect("/tools/accounts/google/login/")
        return self.get_response(request)