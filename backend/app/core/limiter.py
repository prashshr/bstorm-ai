from slowapi import Limiter


def get_real_client_ip(request):
    """Extract real client IP from X-Forwarded-For header (first entry), falling back to direct IP."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_client_ip)
