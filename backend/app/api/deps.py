from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.sessions import get_uek
from app.db.session import get_db
from app.models.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        uek = payload.get("uek")
        sid = payload.get("sid")
        if subject is None:
            raise credentials_exception
        # A refresh token must never authorise an API call on its own: it is
        # long-lived (30 days by default) and is only accepted by
        # /api/auth/refresh. Access tokens do not carry a `type` claim, so
        # tokens without one stay valid for backward compatibility.
        if payload.get("type") == "refresh":
            raise credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    # Web clients carry the UEK directly in the token (legacy flow).
    # Mobile clients carry a server session id (sid); resolve the UEK
    # server-side from the store so it never touches the device.
    if uek is None and sid is not None:
        uek = get_uek(sid)
        if uek is None:
            # The session referenced by this token no longer exists (expired,
            # revoked, or the row is undecryptable). Fail closed instead of
            # silently falling back to the server key, which would encrypt
            # new records outside the user's own encryption key.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired; please sign in again",
            )
    user.uek = uek  # Transient attribute for this request lifecycle
    # Exposed so credential-changing endpoints can tell which server-side
    # session is making the request and preserve just that one.
    user.sid = sid
    return user
