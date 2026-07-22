from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schema.user import UserCreate, UserResponse
from app.core.security import hash_password
from app.models.user import User
from app.api.deps import get_db



router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail='이미 등록된 이메일입니다.')
    
    hash_pw = hash_password(user_in.password)

    new_user = User(email=user_in.email, password_hash=hash.pw)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
