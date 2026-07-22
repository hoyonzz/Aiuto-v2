from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError



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