from pydantic import BaseModel



# 토큰 스키마
class Token(BaseModel):
    access_token: str
    token_type: str