# AI Supply Chain - Santista
## Guia de Instalação e Configuração

---

## Estrutura do projeto

```
supply_chain/
├── app/
│   ├── main.py        ← API FastAPI (endpoints /forecast /inventory /pricing)
│   ├── forecast.py    ← Lógica de previsão de demanda
│   ├── inventory.py   ← Cálculo de ponto de reposição e status
│   └── pricing.py     ← Precificação dinâmica
├── requirements.txt
└── workflow_n8n.json  ← Importar no n8n
```

---

## PASSO 1 — Subir o backend Python

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Subir a API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Teste rápido:
```bash
curl http://localhost:8000/health
# → {"status":"ok"}

curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"data":[{"sku":"SKU-001","client":"Cliente A","sales":300,"stock":500,"cost":12.50}]}'
```

---

## PASSO 2 — Preparar o banco Postgres

```sql
-- Tabela de dados do ERP (origem)
CREATE TABLE sales_data (
  sku     TEXT NOT NULL,
  client  TEXT NOT NULL,
  date    DATE NOT NULL,
  sales   NUMERIC(12,2),
  stock   NUMERIC(12,2),
  cost    NUMERIC(12,4),
  PRIMARY KEY (sku, client, date)
);

-- Tabela de resultados gerados pelo workflow
CREATE TABLE supply_chain_results (
  sku               TEXT NOT NULL,
  client            TEXT NOT NULL,
  forecast_30d      NUMERIC(12,2),
  days_of_stock     NUMERIC(8,1),
  risk              TEXT,
  inventory_status  TEXT,
  suggested_order   NUMERIC(12,2),
  stock_value_brl   NUMERIC(14,2),
  suggested_price   NUMERIC(12,2),
  margin_pct        NUMERIC(6,1),
  pricing_action    TEXT,
  processed_at      TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (sku, client)
);
```

---

## PASSO 3 — Configurar credenciais no n8n

### Postgres
1. n8n → Settings → Credentials → New
2. Tipo: **PostgreSQL**
3. Preencha: host, port (5432), database, user, password
4. Salve e copie o ID gerado
5. Substitua `SEU_CREDENTIAL_ID` no JSON pelos nós **Fetch ERP Data** e **Save to Postgres**

### Slack
1. n8n → Settings → Credentials → New
2. Tipo: **Slack API**
3. Gere um Bot Token em https://api.slack.com/apps
4. Escopos necessários: `chat:write`, `channels:join`
5. Salve e copie o ID gerado
6. Substitua `SEU_SLACK_ID` nos 4 nós de Slack do JSON

---

## PASSO 4 — Importar o workflow no n8n

1. Acesse seu n8n (ex: http://localhost:5678)
2. Menu lateral → **Workflows** → **Import from file**
3. Selecione `workflow_n8n.json`
4. O workflow será carregado com todos os nós
5. Revise as credenciais em cada nó (ícone de chave)

---

## PASSO 5 — Configurar os canais Slack

Crie 3 canais no Slack:
- `#supply-chain-alerts` → alertas de estoque excessivo e crítico
- `#supply-chain-daily`  → relatório diário consolidado
- `#supply-chain-errors` → erros de execução do workflow

Convide o bot para cada canal:
```
/invite @nome-do-seu-bot
```

---

## PASSO 6 — Testar e ativar

1. No n8n, clique em **Execute Workflow** (modo manual) para testar
2. Verifique os logs de cada nó clicando nele
3. Se tudo ok, ative o toggle **Active** no topo
4. O cron vai disparar automaticamente de seg a sex às 08h

---

## Variáveis de ambiente recomendadas (produção)

```bash
# .env
DB_HOST=seu-host-postgres
DB_PORT=5432
DB_NAME=santista_erp
DB_USER=usuario
DB_PASS=senha_segura

API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

Carregue no main.py com `python-dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## O que foi melhorado vs. versão original

| Item | Original | Versão robusta |
|------|----------|----------------|
| Query ERP | `SELECT *` sem filtro | Filtra 30 dias, agrupa por SKU |
| Validação | Só converte tipo | Valida nulos, negativos, SKU vazio |
| Envio API | Item por item | Agrega tudo num único POST |
| Retry | Sem retry | 3 tentativas com backoff de 2s |
| Resultado | Só inventory → check | Merge dos 3 serviços |
| Armazenamento | Sem persistência | Grava em Postgres com UPSERT |
| Alertas Slack | 1 canal, 1 tipo | 3 canais, 3 tipos de alerta |
| Relatório | Sem resumo | Relatório diário consolidado |
| Erros | Workflow para | Error handler → Slack |
| Cron | Todos os dias | Seg-Sex apenas |
