import time
import httpx  # Se não tiver instalado, rode: pip install httpx
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

URL = "http://127.0.0.1:8000/api/v1/relatorios/pdf"

# Busca os dados de teste de forma segura a partir do .env
TEST_NOME = os.getenv("TEST_PACIENTE_NOME")
TEST_NASCIMENTO = os.getenv("TEST_PACIENTE_NASCIMENTO")

if not TEST_NOME or not TEST_NASCIMENTO:
    raise ValueError(
        "Erro: As variáveis TEST_PACIENTE_NOME ou TEST_PACIENTE_NASCIMENTO "
        "não foram configuradas no seu arquivo .env!"
    )

PAYLOAD = {
    "nome": TEST_NOME, 
    "data_nascimento": TEST_NASCIMENTO
}

def rodar_benchmark():
    print("Iniciando teste de performance do gerador de laudos...")
    
    start_time = time.time()
    
    try:
        with httpx.Client() as client:
            # Faz a requisição POST simulando o payload da enfermeira
            response = client.post(URL, json=PAYLOAD, timeout=30.0)
            
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        resultado = (
            f"=== RELATÓRIO DE PERFORMANCE ===\n"
            f"Status Code: {response.status_code}\n"
            f"Tempo total de resposta (API + Banco + WeasyPrint): {duration_ms:.2f} ms\n"
            f"Tamanho do PDF retornado: {len(response.content) / 1024:.2f} KB\n"
        )
        
        print("\n" + resultado)
        
        # DEFINE O CAMINHO DA NOVA PASTA DE SAÍDA
        output_dir = os.path.join("test", "outputs")
        
        # Garante que a pasta 'test/outputs' exista antes de gravar o arquivo
        os.makedirs(output_dir, exist_ok=True)
        
        # Caminho final do arquivo .txt dentro da pasta correta
        output_path = os.path.join(output_dir, "test_performance.txt")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(resultado)
            
        print(f"Resultado salvo com sucesso em: {output_path}")
            
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")
        print("Certifique-se de que o servidor Uvicorn está rodando localmente na porta 8000!")

if __name__ == "__main__":
    rodar_benchmark()