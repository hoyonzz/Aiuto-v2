from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker



SQLALCHEMY_DATABASE_URL = "sqlite:///./aiuto_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    # 1. DB 연결 통로 열기
    db = SessionLocal()
    try:
        # 라우터 함수에게 장부 빌려주기
        yield db
    finally:
        db.close()