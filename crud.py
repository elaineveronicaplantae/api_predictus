from sqlalchemy.orm import Session
from . import models, security

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# --- NOVA FUNÇÃO PARA CRIAR USUÁRIO ---
def create_user(db: Session, user_email: str, user_password: str):
    hashed_password = security.get_password_hash(user_password)
    db_user = models.User(email=user_email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
