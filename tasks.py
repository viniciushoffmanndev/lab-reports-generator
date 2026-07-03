import os
import sys

# 🚀 ENSINA O WINDOWS A ACHAR AS DLLS DO GTK+ LOCALMENTE
GTK_BIN = os.path.join(os.path.dirname(__file__), "libs", "gtk", "bin")
if os.path.exists(GTK_BIN):
    os.environ["PATH"] = GTK_BIN + os.pathsep + os.environ.get("PATH", "")
    if sys.version_info >= (3, 8):
        try:
            os.add_dll_directory(GTK_BIN)
        except Exception:
            pass

# Agora sim os imports pesados podem acontecer de forma segura
import datetime
from celery import Celery
from weasyprint import HTML
from database import buscar_exames_paciente_performance

# 1. Configuração da URL do Redis com o parâmetro de protocolo para o Redis 5
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0?protocol=2")

# 2. Inicialização do Celery
celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL  # Guarda o resultado/status do PDF aqui também
)

# Configurações recomendadas para evitar problemas de concorrência e caminhos no Windows
celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Distribui 1 tarefa por vez por worker
    timezone="America/Sao_Paulo"
)

@celery_app.task(name="tasks.gerar_espelho_pdf_async")
def gerar_espelho_pdf_async(nome_paciente: str, data_nascimento_filtro: str, html_template: str, static_dir: str):
    """
    Tarefa assíncrona que roda em background no Worker do Celery.
    Busca os dados no banco Neon, faz o replace no HTML e compila o WeasyPrint.
    """
    try:
        # 1. Busca os dados usando a sua persistência otimizada com Regex Python
        dados_paciente, exames = buscar_exames_paciente_performance(nome_paciente, data_nascimento_filtro)
        
        if not dados_paciente:
            return {"status": "erro", "motivo": "Paciente não encontrado"}

        # 2. Monta as linhas da tabela em HTML dinamicamente
        linhas_html = ""
        for ex in exames:
            # Lógica das badges baseada no resultado
            resultado = ex['resultado']
            if resultado.lower() == 'pendiente':
                badge_class = 'badge-pending'
            elif resultado.lower() in ['positivo', 'reagente']:
                badge_class = 'badge-positive'
            else:
                badge_class = 'badge-negative'

            linhas_html += f"""
            <tr>
                <td class="code-col">{ex['codigo']}</td>
                <td>{ex['procedimento']}</td>
                <td><span class="{badge_class}">{resultado}</span></td>
                <td>{ex['data_liberacao']}</td>
            </tr>
            """

        # 3. Gera o carimbo de auditoria em português correto
        agora = datetime.datetime.now()
        meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        data_extenso = f"{agora.day} de {meses[agora.month - 1]} de {agora.year}"
        carimbo_completo = f"Relatório gerado em {data_extenso} às {agora.strftime('%H:%M')} horas"

        # 4. Substitui os placeholders no template HTML
        html_renderizado = html_template.replace("{{ nome_paciente }}", dados_paciente['nome'])
        html_renderizado = html_renderizado.replace("{{ data_nascimento }}", dados_paciente['data_nascimento'])
        html_renderizado = html_renderizado.replace("{{ cns_paciente }}", dados_paciente['cns'])
        html_renderizado = html_renderizado.replace("{{ cpf_paciente }}", dados_paciente['cpf'])
        html_renderizado = html_renderizado.replace("{{ nome_mae }}", dados_paciente['nome_mae'])
        html_renderizado = html_renderizado.replace("{{ tabela_linhas }}", linhas_html)
        html_renderizado = html_renderizado.replace("{{ carimbo_geracao_nis }}", carimbo_completo)

        # 5. Define onde o PDF temporário será salvo para o usuário baixar depois
        os.makedirs("test/outputs", exist_ok=True)
        nome_arquivo = f"espelho_{nome_paciente.lower().replace(' ', '_')}_{agora.strftime('%Y%m%d%H%M%S')}.pdf"
        caminho_salvamento = os.path.join("test/outputs", nome_arquivo)

        # 6. Chama o WeasyPrint apontando para a pasta das Libs GTK locais
        # Passamos o static_dir como base_url para ele achar o css/style.css e img/brasao.webp
        HTML(string=html_renderizado, base_url=static_dir).write_pdf(caminho_salvamento)

        return {
            "status": "sucesso", 
            "caminho_pdf": caminho_salvamento,
            "nome_arquivo": nome_arquivo
        }

    except Exception as e:
        # Se algo quebrar no background, o Celery captura e retorna o erro estruturado
        return {"status": "erro", "motivo": str(e)}