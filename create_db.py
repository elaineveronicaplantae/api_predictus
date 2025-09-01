from app.auth.database import engine, Base
from app.auth.models import User

print("INFO:     Criando tabelas do banco de dados...")
Base.metadata.create_all(bind=engine)
print("INFO:     Tabelas do banco de dados criadas com sucesso.")
