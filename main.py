import os
import sys
import io

# Pega o caminho absoluto da pasta raiz do projeto de forma dinâmica
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Conecta até a pasta bin do GTK portável
gtk_bin_path = os.path.join(BASE_DIR, "libs", "gtk", "bin")

if os.path.exists(gtk_bin_path):
    os.environ['PATH'] = gtk_bin_path + os.path.pathsep + os.environ['PATH']
    if sys.version_info >= (3, 8):
        os.add_dll_directory(gtk_bin_path)
else:
    print(f"Aviso: Pasta de DLLs não encontrada em: {gtk_bin_path}")

# -------------------------------------------------------------
# IMPORTS DA API:
# -------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from weasyprint import HTML
from datetime import datetime

# Importa a função otimizada e modularizada
from database import buscar_exames_paciente_performance

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
    nome_busca = request.nome.strip().upper()
    data_string = request.data_nascimento.strip()
    
    try:
        data_busca = datetime.strptime(data_string, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de data de nascimento inválido. Use o padrão YYYY-MM-DD."
        )

    try:
        # Chama a persistência externa que já resolve a sanitização por trás dos panos
        registros = await buscar_exames_paciente_performance(nome_busca, data_busca)
        
        if not registros:
            raise HTTPException(
                status_code=404, 
                detail=f"Nenhum registro encontrado para o paciente '{nome_busca}' com a data de nascimento '{data_busca}'."
            )
        
        # Tratamento de dados do paciente e formatação do carimbo de auditoria do NIS
        cpf_paciente = registros[0]['cpf'] if registros[0]['cpf'] else "Não informado"
        cns_paciente = str(registros[0]['cns']) if registros[0]['cns'] else "Não informado"
        nome_mae = registros[0]['nm_mae'] if registros[0]['nm_mae'] else "Não informado"
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        hoje = datetime.now()
        data_geracao_extenso = f"{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}"
        hora_minuto = hoje.strftime("%H:%M")
        carimbo_hora = f"Relatório gerado em {data_geracao_extenso} às {hora_minuto} hours"
        texto_rodape_completo = carimbo_hora
        
        # Construção dinâmica das linhas da tabela HTML
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
        
        # Leitura do arquivo de template
        template_path = os.path.join(BASE_DIR, "templates", "laudo.html")
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        data_nascimento_br = data_busca.strftime("%d/%m/%Y")

        if len(cpf_paciente) == 11 and cpf_paciente.isdigit():
            cpf_formatado = f"{cpf_paciente[:3]}.{cpf_paciente[3:6]}.{cpf_paciente[6:9]}-{cpf_paciente[9:]}"
        else:
            cpf_formatado = cpf_paciente

        # Cadeia de substituição sequencial
        html_final = html_content.replace("{{ nome_paciente }}", nome_busca)
        html_final = html_final.replace("{{ data_nascimento }}", data_nascimento_br)
        html_final = html_final.replace("{{ cpf_paciente }}", cpf_formatado)
        html_final = html_final.replace("{{ cns_paciente }}", cns_paciente)
        html_final = html_final.replace("{{ nome_mae }}", nome_mae)
        html_final = html_final.replace("{{ carimbo_geracao_nis }}", texto_rodape_completo)
        html_final = html_final.replace("{{ tabela_linhas }}", tabela_linhas)
        
        # Geração do PDF em memória apontando a base_url para a pasta static
        pdf_bytes = HTML(string=html_final, base_url=STATIC_DIR).write_pdf()
        pdf_stream = io.BytesIO(pdf_bytes)
        
        nome_arquivo_slug = nome_busca.replace(" ", "_").lower()
        
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=exame_{nome_arquivo_slug}.pdf"}
        )
        
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"Erro ao processar requisição: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar o laudo médico.")