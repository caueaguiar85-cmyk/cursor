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
<title>Stoken Advisory &mdash; Plataforma de Diagn&oacute;stico Estrat&eacute;gico</title>
<meta name="description" content="Plataforma B2B de diagn&oacute;stico estrat&eacute;gico de supply chain. Stoken Advisory para Santista S.A."/>
<link rel="icon" type="image/png" href="/static/santista.png"/>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<link rel="stylesheet" href="/static/css/style.css"/>
<script>
(function(){
  var t = localStorage.getItem('theme');
  if (!t) t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  if (t === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
})();
</script>
</head>
<body>

<div class="app-layout">

  <!-- ═══ SIDEBAR ═══ -->
  <aside class="sidebar" id="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <span class="sidebar-wordmark">STOKEN</span>
      <span class="sidebar-wordmark-sub">ADVISORY</span>
    </div>

    <!-- Cliente ativo -->
    <div class="sidebar-client">
      <span class="sidebar-client-label">CLIENTE ATIVO</span>
      <span class="sidebar-client-name">Santista S.A.</span>
    </div>

    <div class="sidebar-divider"></div>

    <!-- Menu -->
    <nav class="sidebar-nav">
      <a class="sidebar-item" data-page="projeto" href="#projeto">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
        <span>Projeto</span>
      </a>
      <a class="sidebar-item" data-page="entrevistas" href="#entrevistas">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        <span>Entrevistas</span>
      </a>
      <a class="sidebar-item active" data-page="diagnostico" href="#diagnostico">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <span>Diagn&oacute;stico</span>
      </a>
      <a class="sidebar-item" data-page="insights" href="#insights">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14"/></svg>
        <span>Insights</span>
        <span class="sidebar-badge">&middot; 8</span>
      </a>
      <a class="sidebar-item" data-page="roadmap" href="#roadmap">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>
        <span>Roadmap</span>
      </a>

      <div class="sidebar-divider" style="margin-top: auto;"></div>

      <a class="sidebar-item" data-page="configuracoes" href="#configuracoes">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
        <span>Configura&ccedil;&otilde;es</span>
      </a>
    </nav>

    <!-- Progresso -->
    <div class="sidebar-progress">
      <span class="sidebar-progress-label">PROGRESSO</span>
      <span class="sidebar-progress-value">15%</span>
      <div class="sidebar-progress-bar">
        <div class="sidebar-progress-fill" style="width: 15%"></div>
      </div>
    </div>

    <!-- Collapse toggle -->
    <button class="sidebar-collapse-btn" id="sidebar-collapse" aria-label="Recolher sidebar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="11 17 6 12 11 7"/><polyline points="18 17 13 12 18 7"/></svg>
    </button>
  </aside>

  <!-- ═══ MAIN AREA ═══ -->
  <div class="main-area">

    <!-- Topbar -->
    <header class="topbar">
      <div class="topbar-left">
        <button class="sidebar-mobile-btn" id="sidebar-mobile-btn" aria-label="Abrir menu">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <nav class="breadcrumb">
          <span class="breadcrumb-muted">Santista S.A.</span>
          <span class="breadcrumb-sep">/</span>
          <span class="breadcrumb-current" id="breadcrumb-page">Diagn&oacute;stico</span>
        </nav>
      </div>
      <div class="topbar-right">
        <button class="theme-toggle" id="theme-toggle" aria-label="Alternar tema">
          <span class="icon-sun">&#9788;</span>
          <span class="icon-moon">&#9789;</span>
        </button>
        <div class="topbar-avatar">CA</div>
      </div>
    </header>

    <!-- Content area — pages -->
    <main class="content" id="content">

      <!-- ══ PAGE: PROJETO ══ -->
      <div class="page" id="page-projeto">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Projeto</h1>
            <p class="page-subtitle">Vis&atilde;o geral do diagn&oacute;stico estrat&eacute;gico</p>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <div class="metrics-strip">
          <div class="metric-cell">
            <span class="metric-label">CLIENTE</span>
            <span class="metric-value">Santista S.A.</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">SETOR</span>
            <span class="metric-value">Ind&uacute;stria T&ecirc;xtil</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">IN&Iacute;CIO</span>
            <span class="metric-value font-mono">15 mar 2026</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">STATUS</span>
            <span class="metric-value" style="color: var(--warning)">Em andamento</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">ENTREVISTAS</span>
            <span class="metric-value font-mono">4 / 6</span>
          </div>
          <div class="metric-cell">
            <span class="metric-label">SCORE GERAL</span>
            <span class="metric-value font-mono" style="color: var(--accent)">1.9 / 5.0</span>
          </div>
        </div>

        <div class="projeto-grid">
          <div class="card-section">
            <h2 class="section-heading">Escopo do projeto</h2>
            <p class="body-text">
              Diagn&oacute;stico estrat&eacute;gico de maturidade em supply chain da Santista S.A.,
              cobrindo 5 pilares: Processos, Sistemas &amp; Dados, Opera&ccedil;&otilde;es, Organiza&ccedil;&atilde;o e Roadmap.
              Objetivo: mapear gaps, benchmarking setorial e gerar roadmap de transforma&ccedil;&atilde;o com quick wins.
            </p>
          </div>

          <div class="card-section">
            <h2 class="section-heading">Equipe Stoken</h2>
            <div class="team-list">
              <div class="team-member">
                <div class="team-avatar">CA</div>
                <div class="team-info">
                  <span class="team-name">Cau&ecirc; Aguiar</span>
                  <span class="team-role">Lead Consultant</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">JP</div>
                <div class="team-info">
                  <span class="team-name">Julia Pereira</span>
                  <span class="team-role">Data Analyst</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">MB</div>
                <div class="team-info">
                  <span class="team-name">Marcos Bastos</span>
                  <span class="team-role">AI Engineer</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card-section">
          <h2 class="section-heading">Timeline do projeto</h2>
          <div class="timeline-simple">
            <div class="timeline-item timeline-item--done">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <span class="timeline-date font-mono">01&ndash;10 mar</span>
                <span class="timeline-label">Kickoff &amp; alinhamento</span>
              </div>
            </div>
            <div class="timeline-item timeline-item--done">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <span class="timeline-date font-mono">11&ndash;25 mar</span>
                <span class="timeline-label">Entrevistas com stakeholders</span>
              </div>
            </div>
            <div class="timeline-item timeline-item--active">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <span class="timeline-date font-mono">26 mar&ndash;10 abr</span>
                <span class="timeline-label">An&aacute;lise e diagn&oacute;stico por pilar</span>
              </div>
            </div>
            <div class="timeline-item">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <span class="timeline-date font-mono">11&ndash;20 abr</span>
                <span class="timeline-label">Gera&ccedil;&atilde;o de insights e roadmap</span>
              </div>
            </div>
            <div class="timeline-item">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <span class="timeline-date font-mono">21&ndash;25 abr</span>
                <span class="timeline-label">Apresenta&ccedil;&atilde;o executiva</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ PAGE: ENTREVISTAS ══ -->
      <div class="page" id="page-entrevistas" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Entrevistas</h1>
            <p class="page-subtitle">Coleta de dados prim&aacute;rios com stakeholders</p>
          </div>
          <div class="page-header-actions">
            <button class="btn btn--primary">Nova Entrevista</button>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Entrevistados -->
        <div class="interview-grid">

          <div class="interview-card">
            <div class="interview-card-top">
              <div class="interview-avatar">RM</div>
              <div class="interview-info">
                <span class="interview-name">Ricardo Mendes</span>
                <span class="interview-role">Diretor Industrial</span>
              </div>
              <span class="interview-ai-tag font-mono">AI ANALYZED</span>
            </div>
            <div class="interview-tags">
              <span class="interview-tag" style="color: var(--pilar-processos)">PROCESSOS</span>
              <span class="interview-tag" style="color: var(--pilar-operacoes)">OPERA&Ccedil;&Otilde;ES</span>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono">12 mar 2026</span>
              <span class="interview-duration font-mono">45 min</span>
            </div>
          </div>

          <div class="interview-card">
            <div class="interview-card-top">
              <div class="interview-avatar">CP</div>
              <div class="interview-info">
                <span class="interview-name">Carla Pinheiro</span>
                <span class="interview-role">Gerente Comercial</span>
              </div>
              <span class="interview-ai-tag font-mono">AI ANALYZED</span>
            </div>
            <div class="interview-tags">
              <span class="interview-tag" style="color: var(--pilar-processos)">PROCESSOS</span>
              <span class="interview-tag" style="color: var(--pilar-organizacao)">ORGANIZA&Ccedil;&Atilde;O</span>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono">14 mar 2026</span>
              <span class="interview-duration font-mono">52 min</span>
            </div>
          </div>

          <div class="interview-card">
            <div class="interview-card-top">
              <div class="interview-avatar">LT</div>
              <div class="interview-info">
                <span class="interview-name">Lucas Torres</span>
                <span class="interview-role">Diretor de TI</span>
              </div>
              <span class="interview-ai-tag font-mono">AI ANALYZED</span>
            </div>
            <div class="interview-tags">
              <span class="interview-tag" style="color: var(--pilar-sistemas)">SISTEMAS</span>
              <span class="interview-tag" style="color: var(--pilar-roadmap)">ROADMAP</span>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono">18 mar 2026</span>
              <span class="interview-duration font-mono">38 min</span>
            </div>
          </div>

          <div class="interview-card">
            <div class="interview-card-top">
              <div class="interview-avatar">AF</div>
              <div class="interview-info">
                <span class="interview-name">Ana Farias</span>
                <span class="interview-role">Coord. Qualidade</span>
              </div>
              <span class="interview-ai-tag font-mono">AI ANALYZED</span>
            </div>
            <div class="interview-tags">
              <span class="interview-tag" style="color: var(--pilar-operacoes)">OPERA&Ccedil;&Otilde;ES</span>
              <span class="interview-tag" style="color: var(--pilar-processos)">PROCESSOS</span>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono">20 mar 2026</span>
              <span class="interview-duration font-mono">41 min</span>
            </div>
          </div>

          <!-- Pendentes -->
          <div class="interview-card interview-card--pending">
            <div class="interview-card-top">
              <div class="interview-avatar interview-avatar--empty">&mdash;</div>
              <div class="interview-info">
                <span class="interview-name" style="color: var(--text-muted)">Pendente</span>
                <span class="interview-role">CFO / Diretor Financeiro</span>
              </div>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono" style="color: var(--text-subtle)">A agendar</span>
            </div>
          </div>

          <div class="interview-card interview-card--pending">
            <div class="interview-card-top">
              <div class="interview-avatar interview-avatar--empty">&mdash;</div>
              <div class="interview-info">
                <span class="interview-name" style="color: var(--text-muted)">Pendente</span>
                <span class="interview-role">Ger. Log&iacute;stica</span>
              </div>
            </div>
            <div class="interview-footer">
              <span class="interview-date font-mono" style="color: var(--text-subtle)">A agendar</span>
            </div>
          </div>

        </div>

        <!-- Mapa de Cobertura -->
        <h2 class="section-heading" style="margin-top: var(--space-8); margin-bottom: var(--space-5);">Mapa de Cobertura</h2>
        <div class="coverage-table-wrap">
          <table class="coverage-table">
            <thead>
              <tr>
                <th></th>
                <th><span class="coverage-pilar-header" style="border-color: var(--pilar-processos)">Processos</span></th>
                <th><span class="coverage-pilar-header" style="border-color: var(--pilar-sistemas)">Sistemas</span></th>
                <th><span class="coverage-pilar-header" style="border-color: var(--pilar-operacoes)">Opera&ccedil;&otilde;es</span></th>
                <th><span class="coverage-pilar-header" style="border-color: var(--pilar-organizacao)">Organiza&ccedil;&atilde;o</span></th>
                <th><span class="coverage-pilar-header" style="border-color: var(--pilar-roadmap)">Roadmap</span></th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="coverage-name">R. Mendes</td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-processos)"><span class="font-mono">3</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-operacoes)"><span class="font-mono">5</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
              </tr>
              <tr>
                <td class="coverage-name">C. Pinheiro</td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-processos)"><span class="font-mono">4</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-organizacao)"><span class="font-mono">2</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
              </tr>
              <tr>
                <td class="coverage-name">L. Torres</td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-sistemas)"><span class="font-mono">6</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-roadmap)"><span class="font-mono">3</span></td>
              </tr>
              <tr>
                <td class="coverage-name">A. Farias</td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-processos)"><span class="font-mono">2</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--filled" style="--pilar-color: var(--pilar-operacoes)"><span class="font-mono">4</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
                <td class="coverage-cell coverage-cell--empty"><span class="coverage-dash">&mdash;</span></td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <!-- ══ PAGE: DIAGNOSTICO ══ -->
      <div class="page" id="page-diagnostico">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Diagn&oacute;stico</h1>
            <p class="page-subtitle">Centro de an&aacute;lise estrat&eacute;gica</p>
          </div>
          <div class="page-header-actions">
            <button class="btn btn--ghost">&#9655; Rodar diagn&oacute;stico completo</button>
            <button class="btn btn--ghost">Agente individual &#9662;</button>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Tabs -->
        <div class="tabs">
          <button class="tab active" data-dtab="dashboard">Dashboard</button>
          <button class="tab" data-dtab="pilares">An&aacute;lise por Pilar</button>
          <button class="tab" data-dtab="controles">Controles</button>
        </div>

        <!-- Tab: Dashboard -->
        <div class="dtab-content" id="dtab-dashboard">

          <!-- Grid 12 colunas: radar (8) + sidebar (4) -->
          <div class="diag-grid">

            <!-- Coluna esquerda — Radar de Maturidade -->
            <div class="diag-main">
              <div class="card-section">
                <div class="card-header-row">
                  <div>
                    <h2 class="section-heading">Radar de Maturidade</h2>
                    <p class="card-subtitle">Compara&ccedil;&atilde;o dos 5 pilares vs benchmark setor t&ecirc;xtil</p>
                  </div>
                </div>

                <div class="radar-layout">
                  <div class="radar-score-block">
                    <span class="score-big font-mono">1.9</span>
                    <span class="score-suffix font-mono">/5.0</span>
                    <span class="score-label">SCORE GERAL</span>
                  </div>
                  <div class="radar-description">
                    <p class="body-text-italic">Comparativo dos 5 pilares vs benchmark setor t&ecirc;xtil. Santista apresenta defasagem cr&iacute;tica em Sistemas &amp; Dados e Processos.</p>
                  </div>
                </div>

                <!-- Radar Chart (SVG) -->
                <div class="radar-chart-container">
                  <svg class="radar-chart" viewBox="0 0 400 350" xmlns="http://www.w3.org/2000/svg">
                    <!-- Grid lines -->
                    <g class="radar-grid">
                      <polygon points="200,35 345,148 256,310 144,310 55,148" fill="none" stroke="var(--border)" stroke-width="1"/>
                      <polygon points="200,75 310,162 242,286 158,286 90,162" fill="none" stroke="var(--border)" stroke-width="1"/>
                      <polygon points="200,115 275,176 228,262 172,262 125,176" fill="none" stroke="var(--border)" stroke-width="1"/>
                      <polygon points="200,155 240,190 214,238 186,238 160,190" fill="none" stroke="var(--border)" stroke-width="1"/>
                      <!-- Axis lines -->
                      <line x1="200" y1="35" x2="200" y2="195" stroke="var(--border)" stroke-width="1"/>
                      <line x1="345" y1="148" x2="200" y2="195" stroke="var(--border)" stroke-width="1"/>
                      <line x1="256" y1="310" x2="200" y2="195" stroke="var(--border)" stroke-width="1"/>
                      <line x1="144" y1="310" x2="200" y2="195" stroke="var(--border)" stroke-width="1"/>
                      <line x1="55" y1="148" x2="200" y2="195" stroke="var(--border)" stroke-width="1"/>
                    </g>
                    <!-- Benchmark (dashed) -->
                    <polygon class="radar-benchmark" points="200,83 298,157 238,278 162,278 102,157" fill="none" stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="4,4"/>
                    <!-- Santista (filled) -->
                    <polygon class="radar-santista" points="200,131 252,178 226,250 174,250 148,178" fill="var(--accent)" fill-opacity="0.15" stroke="var(--accent)" stroke-width="1.5"/>
                    <!-- Labels -->
                    <text x="200" y="24" text-anchor="middle" class="radar-label">Processos</text>
                    <text x="360" y="152" text-anchor="start" class="radar-label">Sistemas</text>
                    <text x="268" y="328" text-anchor="middle" class="radar-label">Opera&ccedil;&otilde;es</text>
                    <text x="132" y="328" text-anchor="middle" class="radar-label">Organiza&ccedil;&atilde;o</text>
                    <text x="40" y="152" text-anchor="end" class="radar-label">Roadmap</text>
                  </svg>
                  <div class="radar-legend">
                    <span class="radar-legend-item"><span class="radar-swatch radar-swatch--santista"></span> Santista S.A.</span>
                    <span class="radar-legend-item"><span class="radar-swatch radar-swatch--benchmark"></span> Benchmark setor</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Coluna direita -->
            <div class="diag-side">
              <!-- Maturidade Geral -->
              <div class="card-section">
                <h3 class="card-label-heading">Maturidade Geral</h3>
                <div class="maturity-display">
                  <span class="maturity-number font-mono">1.9</span>
                  <span class="maturity-scale-label">Escala CMMI 1&ndash;5</span>
                </div>
                <div class="cmmi-scale">
                  <div class="cmmi-track">
                    <div class="cmmi-marker" style="left: 22.5%"></div>
                  </div>
                  <div class="cmmi-labels">
                    <span>1</span><span>2</span><span>3</span><span>4</span><span>5</span>
                  </div>
                </div>
              </div>

              <!-- Benchmark do Setor -->
              <div class="card-section">
                <h3 class="card-label-heading">Benchmark do Setor</h3>
                <div class="benchmark-rows">
                  <div class="benchmark-row">
                    <span class="benchmark-label">Santista S.A.</span>
                    <span class="benchmark-value font-mono">1.9</span>
                  </div>
                  <div class="benchmark-row">
                    <span class="benchmark-label">M&eacute;dia do setor</span>
                    <span class="benchmark-value font-mono">3.3</span>
                  </div>
                  <div class="benchmark-row">
                    <span class="benchmark-label">Delta</span>
                    <span class="benchmark-value font-mono" style="color: var(--danger)">&minus;1.4</span>
                  </div>
                </div>
                <p class="benchmark-source">ABIT &mdash; Relat&oacute;rio de Maturidade Digital t&ecirc;xtil 2025</p>
              </div>
            </div>
          </div>

          <!-- Faixa de scores por pilar -->
          <div class="pilar-strip">
            <div class="pilar-cell">
              <span class="pilar-name">Processos</span>
              <span class="pilar-score font-mono">1.8</span>
              <span class="pilar-delta font-mono" style="color: var(--danger)">&minus;1.6</span>
            </div>
            <div class="pilar-cell">
              <span class="pilar-name">Sistemas &amp; Dados</span>
              <span class="pilar-score font-mono">1.5</span>
              <span class="pilar-delta font-mono" style="color: var(--danger)">&minus;2.1</span>
            </div>
            <div class="pilar-cell">
              <span class="pilar-name">Opera&ccedil;&otilde;es</span>
              <span class="pilar-score font-mono">2.3</span>
              <span class="pilar-delta font-mono" style="color: var(--danger)">&minus;0.9</span>
            </div>
            <div class="pilar-cell">
              <span class="pilar-name">Organiza&ccedil;&atilde;o</span>
              <span class="pilar-score font-mono">2.0</span>
              <span class="pilar-delta font-mono" style="color: var(--danger)">&minus;1.2</span>
            </div>
            <div class="pilar-cell">
              <span class="pilar-name">Roadmap</span>
              <span class="pilar-score font-mono">1.9</span>
              <span class="pilar-delta font-mono" style="color: var(--danger)">&minus;1.3</span>
            </div>
          </div>

          <!-- An&aacute;lises por Pilar -->
          <h2 class="section-heading" style="margin-top: var(--space-8); margin-bottom: var(--space-5);">An&aacute;lises por Pilar</h2>
          <div class="pilar-cards-grid">
            <div class="pilar-card" style="border-top-color: var(--pilar-processos)">
              <h3 class="pilar-card-title">Processos</h3>
              <div class="pilar-card-pending">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Aguardando an&aacute;lise</span>
              </div>
              <a class="pilar-card-action" href="#">Gerar agora &rarr;</a>
            </div>
            <div class="pilar-card" style="border-top-color: var(--pilar-sistemas)">
              <h3 class="pilar-card-title">Sistemas &amp; Dados</h3>
              <div class="pilar-card-pending">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Aguardando an&aacute;lise</span>
              </div>
              <a class="pilar-card-action" href="#">Gerar agora &rarr;</a>
            </div>
            <div class="pilar-card" style="border-top-color: var(--pilar-operacoes)">
              <h3 class="pilar-card-title">Opera&ccedil;&otilde;es</h3>
              <div class="pilar-card-pending">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Aguardando an&aacute;lise</span>
              </div>
              <a class="pilar-card-action" href="#">Gerar agora &rarr;</a>
            </div>
            <div class="pilar-card" style="border-top-color: var(--pilar-organizacao)">
              <h3 class="pilar-card-title">Organiza&ccedil;&atilde;o</h3>
              <div class="pilar-card-pending">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Aguardando an&aacute;lise</span>
              </div>
              <a class="pilar-card-action" href="#">Gerar agora &rarr;</a>
            </div>
            <div class="pilar-card" style="border-top-color: var(--pilar-roadmap)">
              <h3 class="pilar-card-title">Roadmap</h3>
              <div class="pilar-card-pending">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                <span>Aguardando an&aacute;lise</span>
              </div>
              <a class="pilar-card-action" href="#">Gerar agora &rarr;</a>
            </div>
          </div>

        </div><!-- /dtab-dashboard -->

        <!-- Tab: Pilares (placeholder) -->
        <div class="dtab-content" id="dtab-pilares" style="display:none">
          <div class="empty-state">
            <svg class="empty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            <p class="empty-text">An&aacute;lise detalhada por pilar dispon&iacute;vel ap&oacute;s execu&ccedil;&atilde;o do diagn&oacute;stico</p>
          </div>
        </div>

        <!-- Tab: Controles (placeholder) -->
        <div class="dtab-content" id="dtab-controles" style="display:none">
          <div class="empty-state">
            <svg class="empty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09"/></svg>
            <p class="empty-text">Painel de controles e configura&ccedil;&otilde;es do diagn&oacute;stico</p>
          </div>
        </div>

      </div>

      <!-- ══ PAGE: INSIGHTS ══ -->
      <div class="page" id="page-insights" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Insights</h1>
            <p class="page-subtitle">Feed de insights gerados pelos agentes de IA</p>
          </div>
          <div class="page-header-actions">
            <span class="page-counter font-mono">8 insights &middot; 6 alto impacto</span>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Top Quick Wins -->
        <div class="quickwins-banner">
          <div class="quickwins-text">
            <h3 class="quickwins-title">Top Quick Wins por ROI</h3>
            <p class="quickwins-subtitle">A&ccedil;&otilde;es de r&aacute;pido retorno identificadas pela an&aacute;lise</p>
          </div>
          <ol class="quickwins-list">
            <li class="quickwins-item">
              <span>Implementar dashboard de KPIs operacionais</span>
              <span class="quickwins-impact font-mono">+R$ 240k</span>
            </li>
            <li class="quickwins-item">
              <span>Automatizar processo de compras recorrentes</span>
              <span class="quickwins-impact font-mono">+R$ 180k</span>
            </li>
            <li class="quickwins-item">
              <span>Digitalizar checklists de qualidade</span>
              <span class="quickwins-impact font-mono">+R$ 95k</span>
            </li>
            <li class="quickwins-item">
              <span>Integrar ERP com planejamento de produ&ccedil;&atilde;o</span>
              <span class="quickwins-impact font-mono">+R$ 320k</span>
            </li>
            <li class="quickwins-item">
              <span>Criar rotina de S&amp;OP mensal estruturada</span>
              <span class="quickwins-impact font-mono">+R$ 150k</span>
            </li>
          </ol>
        </div>

        <!-- Filtros -->
        <div class="insight-filters">
          <button class="insight-filter active" data-filter="all">Todos (8)</button>
          <span class="insight-filter-sep">&middot;</span>
          <button class="insight-filter" data-filter="risco">Riscos (2)</button>
          <span class="insight-filter-sep">&middot;</span>
          <button class="insight-filter" data-filter="oportunidade">Oportunidades (2)</button>
          <span class="insight-filter-sep">&middot;</span>
          <button class="insight-filter" data-filter="quickwin">Quick Wins (2)</button>
          <span class="insight-filter-sep">&middot;</span>
          <button class="insight-filter" data-filter="estrategico">Estrat&eacute;gicos (2)</button>
        </div>

        <!-- Insights Feed -->
        <div class="insights-feed">

          <!-- Insight 1 -->
          <article class="insight-item">
            <div class="insight-tags">
              <span class="insight-tag insight-tag--critical">ALTO IMPACTO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">RISCO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">SISTEMAS &amp; DADOS</span>
            </div>
            <h3 class="insight-title">ERP fora de suporte representa risco cr&iacute;tico de continuidade operacional</h3>
            <p class="insight-body">O sistema ERP atual (vers&atilde;o 2018) perdeu suporte oficial do fornecedor em jan 2025. Falhas recorrentes no m&oacute;dulo fiscal j&aacute; causaram 3 paradas n&atilde;o planejadas no Q1. Sem plano de migra&ccedil;&atilde;o&hellip; <a class="insight-readmore" href="#">ler mais</a></p>
            <div class="insight-meta">
              <div class="insight-meta-item">
                <span class="insight-meta-label">VALOR ESTIMADO</span>
                <span class="insight-meta-value font-mono" style="color: var(--danger)">&minus;R$ 850k/ano</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">ORIGEM</span>
                <span class="insight-meta-value">Entrevista &mdash; Dir. de TI</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">BENCHMARK</span>
                <span class="insight-meta-value insight-meta-italic">78% do setor j&aacute; migrou para cloud ERP</span>
              </div>
            </div>
            <div class="insight-action-block">
              <span class="insight-action-label">A&Ccedil;&Atilde;O SUGERIDA</span>
              <span class="insight-action-text">Iniciar RFP para migra&ccedil;&atilde;o de ERP com foco em m&oacute;dulos fiscal e supply chain. Prazo recomendado: Q3 2026.</span>
            </div>
            <div class="insight-footer">
              <span class="insight-validated font-mono">&#10003; Validado</span>
            </div>
          </article>

          <div class="insight-divider"></div>

          <!-- Insight 2 -->
          <article class="insight-item">
            <div class="insight-tags">
              <span class="insight-tag insight-tag--critical">ALTO IMPACTO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">OPORTUNIDADE</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">PROCESSOS</span>
            </div>
            <h3 class="insight-title">Processo de S&amp;OP inexistente gera desalinhamento entre comercial e produ&ccedil;&atilde;o</h3>
            <p class="insight-body">N&atilde;o existe reuni&atilde;o formal de Sales &amp; Operations Planning. Comercial promete prazos sem consultar capacidade fabril, gerando 23% de pedidos atrasados no &uacute;ltimo trimestre&hellip; <a class="insight-readmore" href="#">ler mais</a></p>
            <div class="insight-meta">
              <div class="insight-meta-item">
                <span class="insight-meta-label">VALOR ESTIMADO</span>
                <span class="insight-meta-value font-mono" style="color: var(--success)">+R$ 420k/ano</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">ORIGEM</span>
                <span class="insight-meta-value">Entrevista &mdash; Ger. Comercial</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">BENCHMARK</span>
                <span class="insight-meta-value insight-meta-italic">92% das empresas l&iacute;deres t&ecirc;m S&amp;OP mensal</span>
              </div>
            </div>
            <div class="insight-action-block">
              <span class="insight-action-label">A&Ccedil;&Atilde;O SUGERIDA</span>
              <span class="insight-action-text">Implementar ciclo de S&amp;OP mensal com participa&ccedil;&atilde;o de Comercial, PCP, Log&iacute;stica e Financeiro. Piloto em 30 dias.</span>
            </div>
            <div class="insight-footer">
              <span class="insight-validated font-mono">&#10003; Validado</span>
            </div>
          </article>

          <div class="insight-divider"></div>

          <!-- Insight 3 -->
          <article class="insight-item">
            <div class="insight-tags">
              <span class="insight-tag">M&Eacute;DIO IMPACTO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">QUICK WIN</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">OPERA&Ccedil;&Otilde;ES</span>
            </div>
            <h3 class="insight-title">Checklists de qualidade manuais causam retrabalho de 12% na linha de fios</h3>
            <p class="insight-body">Inspe&ccedil;&atilde;o de qualidade ainda &eacute; feita em papel. Dados n&atilde;o alimentam indicadores e falhas s&oacute; s&atilde;o detectadas no final do lote. Digitaliza&ccedil;&atilde;o reduziria retrabalho em 60%&hellip; <a class="insight-readmore" href="#">ler mais</a></p>
            <div class="insight-meta">
              <div class="insight-meta-item">
                <span class="insight-meta-label">VALOR ESTIMADO</span>
                <span class="insight-meta-value font-mono" style="color: var(--success)">+R$ 95k/ano</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">ORIGEM</span>
                <span class="insight-meta-value">Entrevista &mdash; Coord. Qualidade</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">BENCHMARK</span>
                <span class="insight-meta-value insight-meta-italic">Checklist digital &eacute; pr&aacute;tica padr&atilde;o no setor</span>
              </div>
            </div>
            <div class="insight-action-block">
              <span class="insight-action-label">A&Ccedil;&Atilde;O SUGERIDA</span>
              <span class="insight-action-text">Adotar ferramenta de checklist digital (ex: Checkify) na linha de fios como piloto. Escalar para tecelagem em 60 dias.</span>
            </div>
            <div class="insight-footer">
              <span class="insight-validated font-mono">&#10003; Validado</span>
            </div>
          </article>

          <div class="insight-divider"></div>

          <!-- Insight 4 -->
          <article class="insight-item">
            <div class="insight-tags">
              <span class="insight-tag insight-tag--critical">ALTO IMPACTO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">ESTRAT&Eacute;GICO</span>
              <span class="insight-tag-sep">&middot;</span>
              <span class="insight-tag">ORGANIZA&Ccedil;&Atilde;O</span>
            </div>
            <h3 class="insight-title">Aus&ecirc;ncia de cultura data-driven limita capacidade de decis&atilde;o da ger&ecirc;ncia</h3>
            <p class="insight-body">Apenas 15% das decis&otilde;es operacionais s&atilde;o baseadas em dados estruturados. Ger&ecirc;ncia m&eacute;dia opera por experi&ecirc;ncia e intui&ccedil;&atilde;o. KPIs existem mas n&atilde;o s&atilde;o revisados&hellip; <a class="insight-readmore" href="#">ler mais</a></p>
            <div class="insight-meta">
              <div class="insight-meta-item">
                <span class="insight-meta-label">VALOR ESTIMADO</span>
                <span class="insight-meta-value font-mono" style="color: var(--success)">+R$ 600k/ano</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">ORIGEM</span>
                <span class="insight-meta-value">Entrevista &mdash; Dir. Industrial</span>
              </div>
              <div class="insight-meta-item">
                <span class="insight-meta-label">BENCHMARK</span>
                <span class="insight-meta-value insight-meta-italic">Empresas data-driven t&ecirc;m 23x mais chance de adquirir clientes</span>
              </div>
            </div>
            <div class="insight-action-block">
              <span class="insight-action-label">A&Ccedil;&Atilde;O SUGERIDA</span>
              <span class="insight-action-text">Programa de letramento em dados para ger&ecirc;ncia m&eacute;dia + dashboard de KPIs operacionais com revis&atilde;o semanal obrigat&oacute;ria.</span>
            </div>
            <div class="insight-footer">
              <span class="insight-validated font-mono">&#10003; Validado</span>
            </div>
          </article>

        </div><!-- /insights-feed -->
      </div>

      <!-- ══ PAGE: ROADMAP ══ -->
      <div class="page" id="page-roadmap" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Roadmap</h1>
            <p class="page-subtitle">Plano de transforma&ccedil;&atilde;o estrat&eacute;gica</p>
          </div>
          <div class="page-header-actions">
            <span class="page-counter font-mono">12 iniciativas &middot; 3 fases</span>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Fase 1 — Quick Wins -->
        <div class="roadmap-phase">
          <div class="roadmap-phase-header">
            <span class="roadmap-phase-tag font-mono">FASE 1</span>
            <span class="roadmap-phase-name">Quick Wins</span>
            <span class="roadmap-phase-period font-mono">Q2 2026</span>
          </div>
          <div class="roadmap-items">
            <div class="roadmap-item">
              <div class="roadmap-marker roadmap-marker--accent"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Implementar dashboard de KPIs operacionais</span>
                <span class="roadmap-item-meta font-mono">Sistemas &middot; 4 semanas &middot; +R$ 240k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker roadmap-marker--accent"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Criar ciclo de S&amp;OP mensal</span>
                <span class="roadmap-item-meta font-mono">Processos &middot; 2 semanas &middot; +R$ 150k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker roadmap-marker--accent"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Digitalizar checklists de qualidade</span>
                <span class="roadmap-item-meta font-mono">Opera&ccedil;&otilde;es &middot; 3 semanas &middot; +R$ 95k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker roadmap-marker--accent"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Automatizar compras recorrentes</span>
                <span class="roadmap-item-meta font-mono">Processos &middot; 6 semanas &middot; +R$ 180k</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Fase 2 — Estruturante -->
        <div class="roadmap-phase">
          <div class="roadmap-phase-header">
            <span class="roadmap-phase-tag font-mono">FASE 2</span>
            <span class="roadmap-phase-name">Estruturante</span>
            <span class="roadmap-phase-period font-mono">Q3&ndash;Q4 2026</span>
          </div>
          <div class="roadmap-items">
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Migra&ccedil;&atilde;o de ERP para plataforma cloud</span>
                <span class="roadmap-item-meta font-mono">Sistemas &middot; 24 semanas &middot; Cr&iacute;tico</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Programa de letramento em dados</span>
                <span class="roadmap-item-meta font-mono">Organiza&ccedil;&atilde;o &middot; 12 semanas &middot; +R$ 600k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Integrar ERP com planejamento de produ&ccedil;&atilde;o</span>
                <span class="roadmap-item-meta font-mono">Sistemas &middot; 16 semanas &middot; +R$ 320k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Redesenho do fluxo de PCP</span>
                <span class="roadmap-item-meta font-mono">Processos &middot; 8 semanas &middot; +R$ 200k</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Fase 3 — Transformacional -->
        <div class="roadmap-phase">
          <div class="roadmap-phase-header">
            <span class="roadmap-phase-tag font-mono">FASE 3</span>
            <span class="roadmap-phase-name">Transformacional</span>
            <span class="roadmap-phase-period font-mono">2027</span>
          </div>
          <div class="roadmap-items">
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">IA preditiva para forecast de demanda</span>
                <span class="roadmap-item-meta font-mono">Sistemas &middot; 20 semanas &middot; Estrat&eacute;gico</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Torre de controle de supply chain</span>
                <span class="roadmap-item-meta font-mono">Opera&ccedil;&otilde;es &middot; 24 semanas &middot; Estrat&eacute;gico</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Automa&ccedil;&atilde;o de pricing din&acirc;mico</span>
                <span class="roadmap-item-meta font-mono">Processos &middot; 16 semanas &middot; +R$ 500k</span>
              </div>
            </div>
            <div class="roadmap-item">
              <div class="roadmap-marker"></div>
              <div class="roadmap-item-content">
                <span class="roadmap-item-title">Centro de excel&ecirc;ncia em dados</span>
                <span class="roadmap-item-meta font-mono">Organiza&ccedil;&atilde;o &middot; Cont&iacute;nuo &middot; Longo prazo</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ PAGE: CONFIGURACOES ══ -->
      <div class="page" id="page-configuracoes" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Configura&ccedil;&otilde;es</h1>
            <p class="page-subtitle">Par&acirc;metros do projeto e integra&ccedil;&otilde;es</p>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <div class="card-section">
          <h2 class="section-heading">API Endpoints</h2>
          <div class="config-links">
            <a href="/docs" class="config-link">
              <span>Swagger UI</span>
              <span class="config-link-arrow">&rarr;</span>
            </a>
            <a href="/redoc" class="config-link">
              <span>ReDoc</span>
              <span class="config-link-arrow">&rarr;</span>
            </a>
            <a href="/health" class="config-link">
              <span>Health Check</span>
              <span class="config-link-arrow">&rarr;</span>
            </a>
          </div>
        </div>
      </div>

    </main>
  </div>
</div>

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
