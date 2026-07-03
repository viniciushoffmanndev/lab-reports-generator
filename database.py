import os
import asyncpg
import re
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
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro crítico ao tentar conectar ao Neon: {e}")
        raise e

async def buscar_exames_paciente_performance(nome_paciente: str, data_nascimento):
    """
    Busca os exames aplicando a sanitização no backend para máxima velocidade de busca por índice.
    """
    # SANITIZAÇÃO NO BACKEND: Limpa espaços extras e colapsa múltiplos espaços em um único espaço em branco
    nome_sanitizado = re.sub(r'\s+', ' ', nome_paciente.strip())

    conn = await get_db_connection()
    try:
        # Query ultra otimizada mapeando busca direta por índice
        query = """
            SELECT DISTINCT ON (er.cd_exame, p.cd_exame_procedimento)
                er.cd_exame,
                p.ds_procedimento,
                er.ds_resultado,   
                er.dt_resultado,
                c.cpf,
                c.dt_nascimento,
                cns.cd_numero_cartao AS cns,
                c.nm_mae
            FROM exame_requisicao er -- Alterado se o nome for esse, mas corrigido no commit para exame_requisicao caso use o padrão
            INNER JOIN exame e ON er.cd_exame = e.cd_exame
            INNER JOIN exame_procedimento p ON er.cd_exame_procedimento = p.cd_exame_procedimento
            INNER JOIN agenda_gra_ate_horario a ON e.nm_paciente = a.nm_paciente
            INNER JOIN usuario_cadsus c ON a.cd_usu_cadsus = c.cd_usu_cadsus
            LEFT JOIN usuario_cadsus_cns cns ON c.cd_usu_cadsus = cns.cd_usu_cadsus AND cns.st_excluido = 0
            WHERE e.nm_paciente = $1
              AND c.dt_nascimento = $2
            ORDER BY er.cd_exame, p.cd_exame_procedimento;
        """
        
        # O nome_sanitizado entra direto no placeholder $1
        rows = await conn.fetch(query, nome_sanitizado, data_nascimento)
        return rows
    finally:
        await conn.close()