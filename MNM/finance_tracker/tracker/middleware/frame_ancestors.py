from django.utils.deprecation import MiddlewareMixin


class FrameAncestorsMiddleware(MiddlewareMixin):
    """Add Content-Security-Policy header to control framing origins.

    Allows framing from the same origin and local dev hosts (127.0.0.1, localhost).
    """

    def process_response(self, request, response):
        policy = "frame-ancestors 'self' http://127.0.0.1:8000 http://localhost:8000;"
        # Use dict-style assignment compatible with various HttpResponse implementations
        response['Content-Security-Policy'] = policy
        return response
