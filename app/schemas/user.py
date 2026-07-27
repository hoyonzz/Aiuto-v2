from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator



# 요청 전용 스키마(클라이언트 -> 서버)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description='8자 이상 필수')
    password_confirm: str = Field(..., min_length=8, description='8자 이상 필수')
    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreate':
        if self.password != self.password_confirm:
            raise ValueError('비밀번호와 비밀번호 확인이 일치하지 않습니다')
        return self

# 응답 전용 스키마(서버 -> 클라이언트)
class UserResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)