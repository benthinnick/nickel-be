from uuid import uuid4

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import Settings, get_settings

_SESSION_SALT = "shekel-session"


def session_serializer(settings: Settings | None = None) -> URLSafeTimedSerializer:
    settings = settings or get_settings()
    return URLSafeTimedSerializer(settings.session_secret, salt=_SESSION_SALT)


def peek_session_id(request: Request) -> str | None:
    settings = get_settings()
    serializer = session_serializer(settings)
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return None
    try:
        loaded = serializer.loads(raw, max_age=settings.session_ttl_seconds)
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None
    if isinstance(loaded, str) and loaded:
        return loaded
    return None


def resolve_session_id(request: Request, response: Response) -> str:
    settings = get_settings()
    serializer = session_serializer(settings)
    session_id = peek_session_id(request)
    if session_id is None:
        session_id = str(uuid4())
        token = serializer.dumps(session_id)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=settings.session_ttl_seconds,
        )
    return session_id
