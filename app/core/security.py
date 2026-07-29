from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

import jwt
from datetime import datetime, timezone, timedelta

from app.core.config import get_settings

settings = get_settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


ph = PasswordHasher()

# 회원가입 시, 비밀번호를 해싱하여 DB저장
def hash_password(plain_password: str) -> str:
    # salting
    hashed = ph.hash(plain_password)
    return hashed

# 로그인 시, 비밀번호 검증
def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return ph.verify(stored_hash, plain_password)
    except VerifyMismatchError:
        return False

# jwt토큰 굽는 함수
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# jwt토큰 해독 함수
def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])