from fastapi import FastAPI, Request, Depends, Cookie, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import pandas as pd
from jose import JWTError
from sqlalchemy.orm import Session
import datetime
import re

# --- Imports de Autenticação e Regras ---
from app.auth import router as auth_router, schemas, crud, security, models
from app.auth.database import SessionLocal, engine
from app.engine.regra_engine import carrega_config, avalia

# --- Função de Limpeza de Dados (do erro 'nan') ---
def clean_data_for_json(obj):
    if isinstance(obj, dict): return {k: clean_data_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list): return [clean_data_for_json(i) for i in obj]
    if pd.isna(obj): return None
    return obj

# --- Configuração Inicial do App e Banco de Dados ---
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- INICIALIZAÇÃO DO APP (LINHA QUE ESTAVA FALTANDO) ---
app = FastAPI(title="API Predictus (quick fix)")

app.include_router(auth_router.router)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
templates = Jinja2Templates(directory="templates")

# "Banco de dados" em memória para os resultados da importação
resultados_db = {}

# --- Lógica de Autenticação ---
async def get_current_user(access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if access_token is None: return None
    try:
        token = access_token.split(" ")[1]
        payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None: return None
    except (JWTError, IndexError):
        return None
    user = crud.get_user_by_email(db, email=email)
    return user

# --- Rotas (Endpoints) ---
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    context = {"request": request, "current_year": datetime.date.today().year, "current_user": None}
    return templates.TemplateResponse("login.html", context)
    
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    context = {"request": request, "current_year": datetime.date.today().year, "current_user": None}
    return templates.TemplateResponse("register.html", context)

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: models.User = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login")
    context = {"request": request, "current_year": datetime.date.today().year, "current_user": current_user}
    return templates.TemplateResponse("index.html", context)

# --- FUNÇÕES DE IMPORTAÇÃO E ACHADOS (COM LÓGICA CPF/CNPJ) ---
@app.post("/importar")
async def importar(arquivo: UploadFile, nome: str = Form(""), cpf_cnpj: str = Form(""), user: models.User = Depends(get_current_user)):
    if not user:
        return JSONResponse({"erro": "Usuário não autenticado."}, status_code=401)
    if not arquivo:
        return JSONResponse({"erro": "Arquivo não enviado."}, status_code=400)

    # Limpa e identifica o documento
    cleaned_doc = re.sub(r'\D', '', cpf_cnpj)
    doc_type = "Desconhecido"
    if len(cleaned_doc) == 11:
        doc_type = "CPF"
    elif len(cleaned_doc) == 14:
        doc_type = "CNPJ"
    print(f"INFO: Documento recebido: {cleaned_doc} (Tipo: {doc_type})")

    try:
        df = pd.read_excel(arquivo.file)
        df = df.where(pd.notna(df), None)
        regras = carrega_config("app/config/regras.json")

        achados = []
        for _, linha in df.iterrows():
            processo_dict = linha.to_dict()
            resultado_avaliacao = avalia(processo_dict, regras)
            if resultado_avaliacao.inclui:
                achados.append(processo_dict)

        resultados_db[cleaned_doc] = achados
        return {"ok": True, "mensagem": f"Análise concluída. {len(achados)} achados encontrados para {nome}."}

    except Exception as e:
        return JSONResponse({"erro": f"Falha ao processar o arquivo: {e}"}, status_code=500)

@app.get("/achados")
def achados(cpf_cnpj: str, user: models.User = Depends(get_current_user)):
    if not user:
        return JSONResponse({"erro": "Usuário não autenticado."}, status_code=401)
    
    # Limpa o documento para a busca
    cleaned_doc = re.sub(r'\D', '', cpf_cnpj)
    
    dados_cliente = resultados_db.get(cleaned_doc, [])
    resumo_agrupado = []

    if dados_cliente:
        df_achados = pd.DataFrame(dados_cliente)
        df_achados['Valor da Causa'] = pd.to_numeric(df_achados['Valor da Causa'], errors='coerce').fillna(0)
        
        summary_df = df_achados.groupby(['Classe Processual', 'Status']).agg(
            quantidade=('N° Processo', 'count'),
            valor_total=('Valor da Causa', 'sum')
        ).reset_index()
        
        resumo_agrupado = summary_df.to_dict('records')

    dados_limpos = clean_data_for_json(dados_cliente)
    return {"cpf_cnpj": cleaned_doc, "total": len(dados_limpos), "resumo": resumo_agrupado, "achados": dados_limpos}
