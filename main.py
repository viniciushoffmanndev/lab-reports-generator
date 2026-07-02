import os
import sys
import io  # <-- CORREÇÃO 1: Faltava importar o io para o BytesIO

# Pega o caminho absoluto da pasta raiz do projeto de forma dinâmica
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Conecta até a pasta bin que você listou no comando tree
gtk_bin_path = os.path.join(BASE_DIR, "libs", "gtk", "bin")

if os.path.exists(gtk_bin_path):
    # Avisa o Windows para incluir essa pasta na busca de executáveis/DLLs
    os.environ['PATH'] = gtk_bin_path + os.path.pathsep + os.environ['PATH']
    
    # Para o Python 3.8 ou superior no Windows, resolve o problema das DLLs locais
    if sys.version_info >= (3, 8):
        os.add_dll_directory(gtk_bin_path)
else:
    print(f"Aviso: Pasta de DLLs não encontrada em: {gtk_bin_path}")

# -------------------------------------------------------------
# IMPORTS DA API:
# -------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field  # <-- CORREÇÃO 2: Faltava importar para validar o PacienteRequest
from weasyprint import HTML
from datetime import datetime

from database import get_db_connection

app = FastAPI(
    title="Lab Reports Generator",
    description="API assíncrona para consulta de exames no Neon e geração de laudos em PDF",
    version="1.0.0"
)

class PacienteRequest(BaseModel):
    nome: str = Field(..., min_length=3, description="Nome completo do paciente")
    data_nascimento: str = Field(..., min_length=10, max_length=10, description="Data de nascimento no formato YYYY-MM-DD")

@app.post("/api/v1/relatorios/pdf")
async def gerar_relatorio_pdf(request: PacienteRequest):
    # 1. Aqui capturamos o nome enviado pelo utilizador
    nome_busca = request.nome.strip().upper()
    
    # 2. Criamos a variável 'data_string' capturando o texto enviado pelo utilizador
    data_string = request.data_nascimento.strip() # Ela guarda o texto puro, ex: '1997-05-20'
    
    try:
        # 3. Aqui convertemos o TEXTO da 'data_string' em um objeto do tipo DATE do Python
        data_busca = datetime.strptime(data_string, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de data de nascimento inválido. Use o padrão YYYY-MM-DD."
        )

    # 1. Conexão com o Banco Neon
    conn = await get_db_connection()
    
    try:
        # Nova Query robusta que cruza os exames com o cadastro central do CadSUS
        query = """
            SELECT 
                er.cd_exame,
                p.ds_procedimento,
                er.ds_resultado,   
                er.dt_resultado,
                c.cpf,
                c.dt_nascimento
            FROM exame_requisicao er
            INNER JOIN exame e ON er.cd_exame = e.cd_exame
            INNER JOIN exame_procedimento p ON er.cd_exame_procedimento = p.cd_exame_procedimento
            INNER JOIN agenda_gra_ate_horario a ON e.nm_paciente = a.nm_paciente
            INNER JOIN usuario_cadsus c ON a.cd_usu_cadsus = c.cd_usu_cadsus
            WHERE e.nm_paciente = $1 
              AND c.dt_nascimento = $2
            ORDER BY er.cd_exame, er.cd_exame_requisicao;
        """
        
        # Executa passando os dois parâmetros obrigatórios de forma segura ($1 e $2)
        registros = await conn.fetch(query, nome_busca, data_busca)
        
        if not registros:
            raise HTTPException(
                status_code=404, 
                detail=f"Nenhum registro encontrado para o paciente '{nome_busca}' com a data de nascimento '{data_busca}'."
            )
        
        # Capturamos o CPF do primeiro registro encontrado para usar no cabeçalho do PDF
        # Se por acaso o CPF estiver nulo no banco, tratamos para não quebrar
        cpf_paciente = registros[0]['cpf'] if registros[0]['cpf'] else "Não informado"
        
        # 2. Construção das linhas da tabela HTML (Prevenção de Nulos)
        tabela_linhas = ""
        for row in registros:
            resultado_bruto = row['ds_resultado'] if row['ds_resultado'] is not None else "Pendente"
            data_resultado = str(row['dt_resultado']) if row['dt_resultado'] else "Aguardando"
            
            if "positivo" in resultado_bruto.lower() or ("reagente" in resultado_bruto.lower() and "não" not in resultado_bruto.lower() and "nao" not in resultado_bruto.lower()):
                res_html = f'<span class="badge-positive">{resultado_bruto}</span>'
            elif "negativo" in resultado_bruto.lower() or "não reagente" in resultado_bruto.lower() or "nao reagente" in resultado_bruto.lower():
                res_html = f'<span class="badge-negative">{resultado_bruto}</span>'
            elif "pendente" in resultado_bruto.lower():
                res_html = f'<span class="badge-pending">{resultado_bruto}</span>'
            else:
                res_html = f'<strong>{resultado_bruto}</strong>'

            tabela_linhas += f"""
                <tr>
                    <td class="code-col">{row['cd_exame']}</td>
                    <td>{row['ds_procedimento']}</td>
                    <td>{res_html}</td>
                    <td>{data_resultado}</td>
                </tr>
            """
        
        # 3. Leitura e Renderização do HTML
        template_path = os.path.join(BASE_DIR, "templates", "laudo.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # FORMA RECOMENDADA: Formata o objeto date diretamente para o padrão BR (Dia/Mês/Ano)
        data_nascimento_br = data_busca.strftime("%d/%m/%Y")

        # Formatamos o CPF adicionando os pontos e traço (ex: 123.456.789-00) caso venha puro do banco
        if len(cpf_paciente) == 11 and cpf_paciente.isdigit():
            cpf_formatado = f"{cpf_paciente[:3]}.{cpf_paciente[3:6]}.{cpf_paciente[6:9]}-{cpf_paciente[9:]}"
        else:
            cpf_formatado = cpf_paciente

        # Substitui os placeholders antigos e os novos no HTML
        html_final = html_content.replace("{{ nome_paciente }}", nome_busca)
        html_final = html_final.replace("{{ data_nascimento }}", data_nascimento_br)
        html_final = html_final.replace("{{ cpf_paciente }}", cpf_formatado)
        html_final = html_final.replace("{{ tabela_linhas }}", tabela_linhas)
        
        # 4. Geração do PDF em memória
        pdf_bytes = HTML(string=html_final).write_pdf()
        pdf_stream = io.BytesIO(pdf_bytes)
        
        nome_arquivo_slug = nome_busca.replace(" ", "_").lower()
        
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=laudo_{nome_arquivo_slug}.pdf"}
        )
        
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar o laudo médico.")
    finally:
        await conn.close()
        