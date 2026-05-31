import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

logger = logging.getLogger("shop.auth")

RUN_MODE = os.getenv("RUN_MODE", "dev").lower()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if RUN_MODE == "prod":
        raise RuntimeError("JWT_SECRET_KEY must be set in production mode")
    SECRET_KEY = "dev-secret-change-in-production"
    logger.warning("Using default JWT_SECRET_KEY - not safe for production!")
if RUN_MODE == "dev":
    logger.warning("RUNNING IN DEV MODE - not safe for production!")

WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 720  # 30 days

security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub", 0))
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except JWTError:
        logger.warning("Token malformed or invalid")
        return None
    except ValueError:
        logger.warning("Token sub field invalid")
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Returns current user or None if not authenticated."""
    if not credentials:
        return None
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        logger.warning("Unauthorized access attempt - 401 returned")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
