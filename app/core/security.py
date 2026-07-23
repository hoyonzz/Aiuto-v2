from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

import jwt
from datetime import datetime, timezone, timedelta



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

SECRET_KEY = "aiuto_v2_super_secret_key_for_development"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# jwt토큰 굽는 함수
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt