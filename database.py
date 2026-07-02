import os
import asyncpg
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db_connection():
    """
    Estabelece e retorna uma conexão assíncrona com o banco de dados Neon.
    """
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi definida no arquivo .env")
    
    try:
        # Abre a conexão assíncrona usando o driver asyncpg
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro crítico ao tentar conectar ao Neon: {e}")
        raise e