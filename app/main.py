"""
AI Supply Chain API - Santista
Backend FastAPI com endpoints de Forecast, Inventory e Pricing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from pydantic import BaseModel, field_validator
from typing import List, Optional
from pathlib import Path
import logging
import traceback

from app.forecast import run_forecast
from app.inventory import run_inventory
from app.pricing import run_pricing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Supply Chain - Santista",
    description="Endpoints de IA para previsão de demanda, estoque e precificação",
    version="1.0.0",
    docs_url=None,      # desabilita o /docs padrão para usarmos um customizado
    redoc_url=None,     # idem para /redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files (logo, favicon) ─────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Landing page ─────────────────────────────────────────────────────────────

LANDING_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>AI Supply Chain — Santista S.A.</title>
<meta name="description" content="Plataforma de IA para otimização de Supply Chain da Santista S.A. Previsão de demanda, gestão de estoque e precificação dinâmica."/>
<link rel="icon" type="image/png" href="/static/santista.png"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/static/css/style.css"/>
</head>
<body>

<!-- Animated Background -->
<div class="bg-grid">
  <div class="bg-orb bg-orb--red"></div>
  <div class="bg-orb bg-orb--blue"></div>
  <div class="bg-orb bg-orb--purple"></div>
</div>

<!-- Navigation -->
<nav class="nav">
  <a class="brand" href="/">
    <img class="brand-logo" src="/static/santista.png" alt="Santista"/>
    <div class="brand-info">
      <span class="brand-name">Santista S.A.</span>
      <span class="brand-sub">AI Supply Chain</span>
    </div>
  </a>
  <div class="nav-links">
    <a class="nav-link nav-link--status" href="/health">
      <span class="status-dot"></span>
      Online
    </a>
    <a class="nav-link" href="/redoc">Docs</a>
    <a class="nav-link" href="#playground">Playground</a>
    <a class="nav-link nav-link--primary" href="/docs">API Docs &#8594;</a>
  </div>
</nav>

<!-- Hero -->
<section class="hero">
  <div class="hero-badge">
    <span class="badge-dot"></span>
    API v1.0.0 &middot; Operacional
  </div>
  <h1>
    Intelig&ecirc;ncia Artificial<br/>
    para sua <span class="gradient-text">Supply Chain</span>
  </h1>
  <p class="hero-description">
    Plataforma de IA da Santista S.A. com previs&atilde;o de demanda, gest&atilde;o inteligente
    de estoque e precifica&ccedil;&atilde;o din&acirc;mica. Decis&otilde;es orientadas por dados em tempo real.
  </p>
  <div class="hero-actions">
    <a class="btn btn--primary" href="/docs">
      <span class="btn-icon">&#9889;</span>
      Explorar API
    </a>
    <a class="btn btn--glass" href="#features">
      <span class="btn-icon">&#10140;</span>
      Ver Recursos
    </a>
  </div>
</section>

<!-- Stats Bar -->
<div class="stats-bar">
  <div class="stats-bar-inner">
    <div class="stat-item">
      <div class="stat-number" data-count="3" data-suffix=" endpoints">0</div>
      <div class="stat-label">Endpoints de IA</div>
    </div>
    <div class="stat-item">
      <div class="stat-number" data-count="95" data-suffix="%">0</div>
      <div class="stat-label">N&iacute;vel de Servi&ccedil;o</div>
    </div>
    <div class="stat-item">
      <div class="stat-number" data-count="30" data-suffix=" dias">0</div>
      <div class="stat-label">Horizonte de Previs&atilde;o</div>
    </div>
    <div class="stat-item">
      <div class="stat-number" data-count="24" data-suffix="/7">0</div>
      <div class="stat-label">Disponibilidade</div>
    </div>
  </div>
</div>

<!-- Features -->
<section class="section" id="features">
  <div class="section-header reveal">
    <div class="section-label">Recursos</div>
    <h2 class="section-title">Tr&ecirc;s pilares de intelig&ecirc;ncia</h2>
    <p class="section-desc">
      Cada endpoint foi calibrado com dados reais da Santista para decis&otilde;es
      precisas no mercado t&ecirc;xtil brasileiro.
    </p>
  </div>

  <div class="features-grid">
    <!-- Forecast -->
    <div class="feature-card reveal reveal-delay-1">
      <div class="feature-icon feature-icon--forecast">
        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      </div>
      <h3>Forecast</h3>
      <p>Previs&atilde;o de demanda de 30 dias por SKU com fator de seguran&ccedil;a 1.30 para absenteismo e risco produtivo. Clientes estrat&eacute;gicos com alerta elevado.</p>
      <div class="feature-endpoint">
        <span class="method-badge">POST</span>
        <span class="endpoint-path">/forecast</span>
      </div>
      <div class="feature-tags">
        <span class="feature-tag">Prophet</span>
        <span class="feature-tag">S&eacute;ries Temporais</span>
        <span class="feature-tag">Risco</span>
      </div>
    </div>

    <!-- Inventory -->
    <div class="feature-card reveal reveal-delay-2">
      <div class="feature-icon feature-icon--inventory">
        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 002 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
      </div>
      <h3>Inventory</h3>
      <p>Ponto de reposi&ccedil;&atilde;o, estoque de seguran&ccedil;a e classifica&ccedil;&atilde;o autom&aacute;tica. Lead time de 7 dias com z-score 1.65 para 95% de servi&ccedil;o.</p>
      <div class="feature-endpoint">
        <span class="method-badge">POST</span>
        <span class="endpoint-path">/inventory</span>
      </div>
      <div class="feature-tags">
        <span class="feature-tag">Safety Stock</span>
        <span class="feature-tag">Reorder Point</span>
        <span class="feature-tag">Alertas</span>
      </div>
    </div>

    <!-- Pricing -->
    <div class="feature-card reveal reveal-delay-3">
      <div class="feature-icon feature-icon--pricing">
        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
      </div>
      <h3>Pricing</h3>
      <p>Pre&ccedil;o din&acirc;mico baseado em custo, margem alvo de 20%, giro e posi&ccedil;&atilde;o de estoque. Piso m&iacute;nimo de 5% de margem para o mercado competitivo.</p>
      <div class="feature-endpoint">
        <span class="method-badge">POST</span>
        <span class="endpoint-path">/pricing</span>
      </div>
      <div class="feature-tags">
        <span class="feature-tag">Margem Din&acirc;mica</span>
        <span class="feature-tag">Premium/Desconto</span>
        <span class="feature-tag">CMV</span>
      </div>
    </div>
  </div>
</section>

<!-- Dashboard Preview -->
<div class="dashboard-preview reveal">
  <div class="section-header">
    <div class="section-label">Dashboard</div>
    <h2 class="section-title">Vis&atilde;o em tempo real</h2>
    <p class="section-desc">
      Monitore KPIs cr&iacute;ticos da cadeia de suprimentos com dados processados pela IA.
    </p>
  </div>

  <div class="dashboard-frame">
    <div class="dash-toolbar">
      <div class="dash-dots">
        <span class="dash-dot dash-dot--red"></span>
        <span class="dash-dot dash-dot--yellow"></span>
        <span class="dash-dot dash-dot--green"></span>
      </div>
      <div class="dash-title">supply-chain-dashboard.santista.ai</div>
      <div class="dash-actions"></div>
    </div>
    <div class="dash-content">
      <div class="dash-sidebar">
        <div class="dash-menu-label">Menu</div>
        <div class="dash-menu-item active">
          <span class="dash-menu-icon">&#9881;</span> Overview
        </div>
        <div class="dash-menu-item">
          <span class="dash-menu-icon">&#9889;</span> Forecast
        </div>
        <div class="dash-menu-item">
          <span class="dash-menu-icon">&#128230;</span> Inventory
        </div>
        <div class="dash-menu-item">
          <span class="dash-menu-icon">&#128176;</span> Pricing
        </div>
        <div class="dash-menu-label">Integra&ccedil;&otilde;es</div>
        <div class="dash-menu-item">
          <span class="dash-menu-icon">&#128268;</span> n8n Workflows
        </div>
        <div class="dash-menu-item">
          <span class="dash-menu-icon">&#128172;</span> Slack Alerts
        </div>
      </div>
      <div class="dash-main">
        <div class="dash-cards">
          <div class="dash-card">
            <div class="dash-card-label">SKUs Monitorados</div>
            <div class="dash-card-value dash-card-value--blue">247</div>
            <div class="dash-card-change dash-card-change--up">&#9650; +12 esta semana</div>
          </div>
          <div class="dash-card">
            <div class="dash-card-label">Estoque Cr&iacute;tico</div>
            <div class="dash-card-value dash-card-value--amber">18</div>
            <div class="dash-card-change dash-card-change--down">&#9660; -3 vs ontem</div>
          </div>
          <div class="dash-card">
            <div class="dash-card-label">Margem M&eacute;dia</div>
            <div class="dash-card-value dash-card-value--green">21.4%</div>
            <div class="dash-card-change dash-card-change--up">&#9650; +0.8pp</div>
          </div>
        </div>
        <div class="dash-chart">
          <div class="dash-chart-header">
            <div class="dash-chart-title">Demanda vs Estoque (30 dias)</div>
            <div class="dash-chart-legend">
              <div class="dash-legend-item">
                <span class="dash-legend-dot" style="background:var(--red)"></span> Demanda
              </div>
              <div class="dash-legend-item">
                <span class="dash-legend-dot" style="background:#3B82F6"></span> Estoque
              </div>
            </div>
          </div>
          <div class="chart-area">
            <div class="chart-bars">
              <div class="chart-bar chart-bar--red" data-height="65%"></div>
              <div class="chart-bar chart-bar--blue" data-height="80%"></div>
              <div class="chart-bar chart-bar--red" data-height="45%"></div>
              <div class="chart-bar chart-bar--blue" data-height="70%"></div>
              <div class="chart-bar chart-bar--red" data-height="75%"></div>
              <div class="chart-bar chart-bar--blue" data-height="60%"></div>
              <div class="chart-bar chart-bar--red" data-height="55%"></div>
              <div class="chart-bar chart-bar--blue" data-height="85%"></div>
              <div class="chart-bar chart-bar--red" data-height="90%"></div>
              <div class="chart-bar chart-bar--blue" data-height="50%"></div>
              <div class="chart-bar chart-bar--red" data-height="70%"></div>
              <div class="chart-bar chart-bar--blue" data-height="75%"></div>
              <div class="chart-bar chart-bar--red" data-height="60%"></div>
              <div class="chart-bar chart-bar--blue" data-height="65%"></div>
              <div class="chart-bar chart-bar--red" data-height="80%"></div>
              <div class="chart-bar chart-bar--blue" data-height="55%"></div>
              <div class="chart-bar chart-bar--red" data-height="50%"></div>
              <div class="chart-bar chart-bar--blue" data-height="90%"></div>
              <div class="chart-bar chart-bar--red" data-height="85%"></div>
              <div class="chart-bar chart-bar--blue" data-height="70%"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- API Playground -->
<section class="playground" id="playground">
  <div class="section-header reveal">
    <div class="section-label">Playground</div>
    <h2 class="section-title">Teste a API ao vivo</h2>
    <p class="section-desc">
      Explore os endpoints com dados reais de exemplo do mercado t&ecirc;xtil brasileiro.
    </p>
  </div>

  <div class="playground-container reveal">
    <!-- Request -->
    <div class="playground-panel">
      <div class="playground-panel-header">
        <span class="playground-panel-title">Request</span>
        <button class="btn--run" id="run-btn">
          <span class="btn-icon">&#9655;</span> Executar
        </button>
      </div>
      <div class="playground-tabs">
        <button class="playground-tab active" data-endpoint="forecast">Forecast</button>
        <button class="playground-tab" data-endpoint="inventory">Inventory</button>
        <button class="playground-tab" data-endpoint="pricing">Pricing</button>
      </div>
      <div class="code-block" id="request-code"></div>
    </div>

    <!-- Response -->
    <div class="playground-panel">
      <div class="playground-panel-header">
        <span class="playground-panel-title">Response</span>
        <span class="response-status response-status--ok" id="response-status">200 OK</span>
      </div>
      <div class="code-block" id="response-code" style="margin-top:40px"></div>
    </div>
  </div>
</section>

<!-- Architecture -->
<section class="section" id="architecture">
  <div class="section-header reveal">
    <div class="section-label">Arquitetura</div>
    <h2 class="section-title">Stack de produ&ccedil;&atilde;o</h2>
    <p class="section-desc">
      Infraestrutura projetada para confiabilidade e integra&ccedil;&atilde;o cont&iacute;nua.
    </p>
  </div>

  <div class="arch-grid reveal">
    <div class="arch-card">
      <span class="arch-icon">&#128640;</span>
      <h4>FastAPI</h4>
      <p>Backend async de alta performance com valida&ccedil;&atilde;o autom&aacute;tica via Pydantic</p>
    </div>
    <div class="arch-card">
      <span class="arch-icon">&#129504;</span>
      <h4>Motor de IA</h4>
      <p>Prophet + pandas + numpy para an&aacute;lise preditiva e otimiza&ccedil;&atilde;o</p>
    </div>
    <div class="arch-card">
      <span class="arch-icon">&#9881;</span>
      <h4>n8n Workflows</h4>
      <p>Automa&ccedil;&atilde;o di&aacute;ria Seg-Sex 08h com retry e tratamento de erros</p>
    </div>
    <div class="arch-card">
      <span class="arch-icon">&#128225;</span>
      <h4>Slack Alerts</h4>
      <p>3 canais de notifica&ccedil;&atilde;o: alertas, relat&oacute;rio di&aacute;rio e erros</p>
    </div>
  </div>
</section>

<!-- Integrations -->
<section class="section">
  <div class="section-header reveal">
    <div class="section-label">Integra&ccedil;&otilde;es</div>
    <h2 class="section-title">Conecte com seu ecossistema</h2>
  </div>

  <div class="integrations-row reveal">
    <div class="integration-item">
      <span class="integration-icon">&#128450;</span>
      <div class="integration-info">
        <span class="integration-name">PostgreSQL</span>
        <span class="integration-desc">ERP &middot; Dados de vendas</span>
      </div>
    </div>
    <div class="integration-item">
      <span class="integration-icon">&#128268;</span>
      <div class="integration-info">
        <span class="integration-name">n8n</span>
        <span class="integration-desc">Automa&ccedil;&atilde;o &middot; Workflows</span>
      </div>
    </div>
    <div class="integration-item">
      <span class="integration-icon">&#128172;</span>
      <div class="integration-info">
        <span class="integration-name">Slack</span>
        <span class="integration-desc">Alertas &middot; Relat&oacute;rios</span>
      </div>
    </div>
    <div class="integration-item">
      <span class="integration-icon">&#9729;</span>
      <div class="integration-info">
        <span class="integration-name">Railway / Heroku</span>
        <span class="integration-desc">Deploy &middot; Hosting</span>
      </div>
    </div>
  </div>
</section>

<!-- CTA -->
<section class="cta-section">
  <div class="cta-box reveal">
    <h2>Pronto para otimizar sua <span class="gradient-text">Supply Chain</span>?</h2>
    <p>Acesse a documenta&ccedil;&atilde;o interativa e comece a integrar em minutos.</p>
    <div class="hero-actions">
      <a class="btn btn--primary" href="/docs">
        <span class="btn-icon">&#128218;</span>
        Documenta&ccedil;&atilde;o Interativa
      </a>
      <a class="btn btn--glass" href="/redoc">
        <span class="btn-icon">&#128196;</span>
        ReDoc
      </a>
    </div>
  </div>
</section>

<!-- Footer -->
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-left">
      <div class="footer-brand">
        <img src="/static/santista.png" alt="Santista"/>
        <span>Santista S.A.</span>
      </div>
      <div class="footer-copy">
        &copy; 2026 <strong>Santista S.A.</strong> &middot; AI Supply Chain Platform &middot; Todos os direitos reservados
      </div>
    </div>
    <div class="footer-links">
      <a class="footer-link" href="/docs">API Docs</a>
      <a class="footer-link" href="/redoc">ReDoc</a>
      <a class="footer-link" href="/health">Status</a>
    </div>
  </div>
</footer>

<script src="/static/js/app.js"></script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing():
    return HTMLResponse(content=LANDING_HTML)


# ─── Custom Swagger & ReDoc ───────────────────────────────────────────────────

@app.get("/docs", include_in_schema=False)
def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " — API Docs",
        swagger_favicon_url="/static/santista.png",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "list",
            "filter": True,
            "syntaxHighlight.theme": "monokai",
        },
    )


@app.get("/redoc", include_in_schema=False)
def custom_redoc():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " — ReDoc",
        redoc_favicon_url="/static/santista.png",
    )


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SkuItem(BaseModel):
    sku: str
    client: str
    sales: float
    stock: float
    cost: float

    @field_validator("sales", "stock", "cost", mode="before")
    @classmethod
    def coerce_numeric(cls, v):
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido: {v}")


class RequestPayload(BaseModel):
    data: List[SkuItem]


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ─── Forecast ─────────────────────────────────────────────────────────────────

@app.post("/forecast")
def forecast(payload: RequestPayload):
    """
    Recebe lista de SKUs e retorna previsão de demanda para os próximos 30 dias.
    Usa Prophet para séries temporais ou fallback com média móvel.
    """
    try:
        logger.info(f"/forecast → {len(payload.data)} itens recebidos")
        results = run_forecast([item.model_dump() for item in payload.data])
        logger.info(f"/forecast → {len(results)} previsões geradas")
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"/forecast erro: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Inventory ────────────────────────────────────────────────────────────────

@app.post("/inventory")
def inventory(payload: RequestPayload):
    """
    Calcula ponto de reposição, estoque de segurança e status de cada SKU.
    Retorna flag de alerta para estoque excessivo ou crítico.
    """
    try:
        logger.info(f"/inventory → {len(payload.data)} itens recebidos")
        results = run_inventory([item.model_dump() for item in payload.data])
        logger.info(f"/inventory → processados {len(results)} SKUs")
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"/inventory erro: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Pricing ──────────────────────────────────────────────────────────────────

@app.post("/pricing")
def pricing(payload: RequestPayload):
    """
    Sugere preço dinâmico com base em custo, margem alvo, giro e posição de estoque.
    """
    try:
        logger.info(f"/pricing → {len(payload.data)} itens recebidos")
        results = run_pricing([item.model_dump() for item in payload.data])
        logger.info(f"/pricing → precificados {len(results)} SKUs")
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(f"/pricing erro: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
