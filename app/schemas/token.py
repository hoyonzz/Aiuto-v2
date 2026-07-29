from pydantic import BaseModel



# 토큰 스키마
class Token(BaseModel):
    access_token: str
    token_type: str

# 토큰 페이로드 내부의 sub를 담아둘 바구니
class TokenData(BaseModel):
    email: str | None = None