<p align="center">
  <img src="https://img.shields.io/badge/PYTHON-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FASTAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/JINJA2-B41717?style=for-the-badge&logo=jinja&logoColor=white" />
  <img src="https://img.shields.io/badge/WEASYPRINT-525M88?style=for-the-badge&logo=render&logoColor=white" />
</p>

<h2 align="center">🏥 Lab Reports Generator — NIS 🏥</h2>

---

## 🎯 Objetivo do Projeto

Gerador automatizado e padronizado de documentos ambulatoriais para o **Núcleo de Informação em Saúde (NIS)** da Prefeitura da Estância Turística de Paraguaçu Paulista. O sistema consome dados brutos de exames lançados após a triagem, cruza informações cadastrais do CadSUS e gera o **Espelho de Exames Laboratoriais**, um documento oficial em PDF altamente legível e otimizado tanto para auditoria interna quanto para o paciente levar para casa.

---

## ✨ Funcionalidades

* **Geração de PDF Clínico**: Conversão fiel de layouts complexos HTML5/CSS para formato A4.
* **Tratamento Dinâmico CadSUS**: Validação com travas de segurança (`fallback`) que injetam automaticamente "Não informado" para CPFs, CNSs ou nomes de mãe ausentes no banco.
* **Cabeçalhos Fluidos**: Layout inteligente que exibe o Brasão e dados municipais na primeira página e um cabeçalho técnico reduzido nas páginas seguintes.
* **Carimbo de Auditoria**: Emissão de rodapé integrado contendo a data de geração por extenso e o horário exato (`HH:MM`) em formato de texto.
* **Otimização de Query Backend**: Sanitização de strings via expressões regulares executadas diretamente no Python, mitigando custos de processamento no banco de dados e aproveitando índices B-Tree nativos.
* **Suíte de Benchmark nativa**: Módulo de testes integrado para validação segura de tempo de resposta, status codes HTTP e tamanho final dos arquivos processados.

---

## 📂 Estrutura do Projeto

```text
LAB-REPORTS-GENERATOR/
├── 📁 libs/             # Binários portáveis do GTK+ (Core gráfico do WeasyPrint para Windows)
│   └── 📁 gtk/bin/      # DLLs nativas essenciais (Cairo, Pango, Pixman, GLib, etc.)
├── 📁 static/           # Arquivos estáticos globais da aplicação
│   └── 📁 img/          # Banco de mídias e assets visuais do sistema
│       └── brasao.webp  # Brasão Oficial da Estância Turística de Paraguaçu Paulista
├── 📁 templates/        # Estrutura de visualização e marcação (Jinja2)
│   └── laudo.html       # Template base parametrizado com CSS Paged Media
├── 📁 test/             # Suíte de testes automatizados e validação de carga
│   ├── 📁 outputs/      # Relatórios de benchmark e tempos de resposta (Ignorado no Git)
│   └── test_performance.py # Script assíncrono seguro de medição de milissegundos
├── .env                 # Variáveis de ambiente e credenciais sensíveis (Ignorado no Git)
├── .gitignore           # Filtros de arquivos e diretórios locais para versionamento
├── database.py          # Pool de conexões, sanitização Python e execução de queries com índice
├── main.py              # Endpoints FastAPI, regras de negócio e motor WeasyPrint
├── LICENSE              # Licença de uso e distribuição do software
├── README.md            # Documentação técnica do sistema (Este arquivo)
└── requirements.txt     # Dependências e pacotes Python do ecossistema
```

---

## 🧠 Arquitetura do Sistema

O sistema foi estruturado com foco em portabilidade autônoma em servidores Windows e isolamento de responsabilidades:

## ⚙️ Engine de Renderização & Dependências (/libs & /templates)

**database.py:** Camada que extrai os dados, realiza o tratamento preventivo de strings vazias e executa a limpeza completa de múltiplos espaços em branco no nome do paciente usando a CPU do Python. Isso garante que o parâmetro enviado ao banco de dados Neon faça uma busca direta indexada (Index Scan), reduzindo os tempos de resposta da query ao mínimo.

**main.py:** Camada de API que orquestra os dados limpos vindos da persistência, monta o payload e injeta no template engine Jinja2 para alimentar o arquivo templates/laudo.html.

**Portabilidade Gráfica do WeasyPrint:** Para evitar instalações complexas ou dependência de pacotes a nível de sistema operacional do servidor Windows, a pasta libs/gtk/bin/ distribui localmente as DLLs em C/C++ nativas do ecossistema GNOME:
* **libcairo-2.dll / libpixman-1-0.dll:** Desenho vetorial e renderização geométrica.
* **libpango-1.0-0.dll / libfontconfig-1.dll:** Mapeamento tipográfico e fontes.
* **libxml2-2.dll / libxslt-1.dll:** Processamento estrutural do HTML.

---

## ⏱️ Suíte de Benchmark & Performance
Para garantir a estabilidade do sistema e mensurar o tempo gasto no processamento do WeasyPrint (compilação gráfica do PDF em memória), o projeto conta com um script de teste seguro alimentado por variáveis locais do .env.
Para executar a medição de performance sem expor dados reais de pacientes em produção, configure o seu ```.env``` local e execute:

```Bash
python test/test_performance.py
```

Os resultados consolidados contendo Status Code, Tamanho do arquivo (KB) e Tempo total (ms) serão impressos em tempo real na tela e gravados de forma isolada na pasta test/outputs/test_performance.txt.

---

### 🔀 Diagrama de Sequência e Ciclo de Vida do Relatório

O diagrama de sequência abaixo ilustra de forma técnica a jornada da informação e a interação entre os componentes do sistema, desde a entrada do paciente até o recebimento do documento impresso:

```mermaid
sequenceDiagram
    autonumber
    actor P as Paciente
    actor E as Enfermeira (NIS)
    participant API as FastAPI (main.py)
    participant DB as Persistência (database.py)
    participant Neon as Neon DB (PostgreSQL)
    participant WP as WeasyPrint (Engine + Libs)

    P->>E: Realiza Triagem / Coleta Exames
    Note over E, Neon: Valores dos exames são digitados e salvos nas tabelas
    E->>API: Solicita "Espelho de Exames" (POST /api/v1/relatorios/pdf)
    activate API
    
    API->>DB: Chama buscar_exames_paciente_performance(nome, data)
    activate DB
    Note over DB: Python aplica Regex (re.sub)<br/>Sanitiza espaços extras na CPU do backend
    
    DB->>Neon: Executa Query Otimizada (Busca direta por Índice B-Tree)
    activate Neon
    Neon-->>DB: Retorna linhas filtradas (Fast Index Scan)
    deactivate Neon
    
    DB-->>API: Retorna dados estruturados (com fallbacks CadSUS)
    deactivate DB
  
    Note over API: Jinja2 injeta os dados estruturados no templates/laudo.html
  
    API->>WP: Envia HTML compilado + Caminho das DLLs (libs/gtk/bin)
    activate WP
    Note over WP: Aplica CSS Paged Media<br/>Evita quebra de linhas (tr avoid)
    WP-->>API: Retorna o binário do PDF montado (BytesIO)
    deactivate WP
  
    API-->>E: Transmite o StreamingResponse do PDF
    deactivate API
    E->>P: Entrega a folha impressa (Espelho de Exames)
```

---

# Regras Normativas de Layout Aplicadas

O documento foi projetado sob réguas de design clínico e legibilidade hospitalar:

**Quebras de Página Inteligentes:** Configurado via CSS Paged Media (tr { page-break-inside: avoid; }) para impedir que uma linha de resultado de exame longo (como o Hemograma) seja fatiada horizontalmente entre duas páginas.

**Hierarquia Tipográfica:** O título principal recebe destaque com tamanho expandido (18px) contrastando com os dados da tabela em fonte compacta (10px). Isso otimiza o escaneamento visual para a enfermagem e reduz o desperdício de papel/toner.

**Cabeçalhos Fluidos:** Primeira página dedicada ao Brasão e Identificação Municipal. Páginas secundárias limpas, exibindo apenas o cabeçalho técnico simplificado do NIS.

**Carimbo de Auditoria:** Rodapé dinâmico integrado que exibe de forma clara a data por extenso e o horário exato da geração (.strftime("%H:%M")) para controle de retirada.

---

## 🚀 Como Executar o Projeto Localmente

1. Configure o Ambiente Virtual:

```Bash
python -m venv venv
.\venv\Scripts\activate
```

2. Instale as Dependências:

```Bash
pip install -r requirements.txt
```

3. Defina as Variáveis no .env:
   Crie um arquivo .env na raiz preenchendo as strings de conexão com o banco de dados da triagem.
4. Inicie o Servidor:

```Bash
uvicorn main:app --reload
```

Acesse a interface de testes em: http://127.0.0.1:8000/docs
