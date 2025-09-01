from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import crud, schemas, security
from .database import SessionLocal

ACCESS_TOKEN_EXPIRE_MINUTES = security.ACCESS_TOKEN_EXPIRE_MINUTES
ALLOWED_DOMAIN = "@plantaeagrocredito.com.br"

router = APIRouter(
    tags=["auth"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/token")
async def login_for_access_token(response: Response, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    # --- LÓGICA DE LOGIN ATUALIZADA ---
    username = form_data.username
    # Se o email não contiver '@', adiciona o domínio padrão
    if "@" not in username:
        username += ALLOWED_DOMAIN
    
    user = crud.get_user_by_email(db, email=username)
    
    # Redireciona para cadastro se o usuário não existe mas o domínio é permitido
    if not user and username.endswith(ALLOWED_DOMAIN):
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado. Realize o primeiro cadastro.",
        )

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {"message": "Login successful"}

# --- Endpoint de Cadastro (sem alterações) ---
@router.post("/register")
async def register_user(db: Session = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    if not email.endswith(ALLOWED_DOMAIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cadastro permitido apenas para e-mails do domínio {ALLOWED_DOMAIN}",
        )
    
    db_user = crud.get_user_by_email(db, email=email)
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")
    
    crud.create_user(db=db, user_email=email, user_password=password)
    return {"message": "Usuário cadastrado com sucesso."}
