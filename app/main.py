"""
AI Supply Chain API - Santista
Backend FastAPI com endpoints de Forecast, Inventory e Pricing
"""

from fastapi import FastAPI, HTTPException, Request, Response, Cookie, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from pydantic import BaseModel, field_validator
from typing import List, Optional
from pathlib import Path
import io
import logging
import traceback

from app.forecast import run_forecast
from app.inventory import run_inventory
from app.pricing import run_pricing
from app.agents import get_all_agents, get_agent, run_agent
from app.datastore import (
    save_interview, get_interviews, get_interview, update_interview,
    delete_interview,
    get_analysis_results, get_analysis_results_for_area,
    get_available_areas, get_pipeline_status
)
from app.pipeline import run_full_pipeline, run_area_pipeline, run_strategy_pipeline
from app.docgen import generate_form_docx, parse_form_docx
from app.auth import (
    authenticate, create_session, get_session_user, destroy_session,
    get_all_users, create_user, update_user, delete_user,
    has_permission, ROLES
)

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


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def _get_current_user(request: Request):
    token = request.cookies.get("session")
    return get_session_user(token) if token else None


# ─── Login page ───────────────────────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Stoken Advisory &mdash; Login</title>
<link rel="icon" type="image/png" href="/static/santista.png"/>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;500&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#FAFAF7;--bg-elevated:#FFF;--bg-subtle:#F2F1EC;--border:#E6E4DD;--border-strong:#C9C6BC;--text:#1A1815;--text-muted:#6B6860;--text-subtle:#9B988F;--accent:#8B1D1D;--font-serif:'Source Serif 4',Georgia,serif;--font-sans:'Inter',system-ui,sans-serif;--font-mono:'JetBrains Mono',monospace}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font-sans);background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center}
.login-container{width:100%;max-width:400px;padding:24px}
.login-logo{text-align:center;margin-bottom:48px}
.login-logo-mark{font-family:var(--font-serif);font-size:20px;font-weight:500;letter-spacing:0.02em;text-transform:uppercase}
.login-logo-sub{font-size:11px;color:var(--text-subtle);letter-spacing:0.08em;text-transform:uppercase;display:block;margin-top:2px}
.login-card{background:var(--bg-elevated);border:1px solid var(--border);border-radius:6px;padding:32px}
.login-title{font-family:var(--font-serif);font-size:20px;font-weight:500;margin-bottom:4px}
.login-subtitle{font-size:13px;color:var(--text-muted);margin-bottom:24px}
.login-form{display:flex;flex-direction:column;gap:16px}
.login-field{display:flex;flex-direction:column;gap:6px}
.login-label{font-size:11px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:var(--text-muted)}
.login-input{font-family:var(--font-sans);font-size:14px;padding:8px 12px;border:1px solid var(--border);border-radius:4px;background:var(--bg);color:var(--text);height:36px}
.login-input:focus{outline:none;border-color:var(--accent)}
.login-btn{font-family:var(--font-sans);font-size:14px;font-weight:500;padding:10px;border:none;border-radius:4px;background:var(--text);color:var(--bg);cursor:pointer;transition:opacity 0.15s}
.login-btn:hover{opacity:0.85}
.login-error{font-size:13px;color:var(--accent);text-align:center;display:none}
.login-footer{text-align:center;margin-top:24px;font-size:11px;color:var(--text-subtle)}
.login-footer strong{color:var(--text-muted);font-weight:500}
</style>
</head>
<body>
<div class="login-container">
  <div class="login-logo">
    <span class="login-logo-mark">STOKEN</span>
    <span class="login-logo-sub">ADVISORY</span>
  </div>
  <div class="login-card">
    <h1 class="login-title">Entrar</h1>
    <p class="login-subtitle">Acesse a plataforma de diagn&oacute;stico estrat&eacute;gico</p>
    <form class="login-form" id="login-form">
      <div class="login-field">
        <label class="login-label">Usu&aacute;rio</label>
        <input class="login-input" type="text" id="login-user" placeholder="seu.usuario" required autofocus />
      </div>
      <div class="login-field">
        <label class="login-label">Senha</label>
        <input class="login-input" type="password" id="login-pass" placeholder="&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;&#8226;" required />
      </div>
      <p class="login-error" id="login-error">Usu&aacute;rio ou senha inv&aacute;lidos</p>
      <button class="login-btn" type="submit">Entrar</button>
    </form>
  </div>
  <p class="login-footer">&copy; 2026 <strong>Stoken Advisory</strong> &middot; Plataforma de Diagn&oacute;stico Estrat&eacute;gico</p>
</div>
<script>
document.getElementById('login-form').addEventListener('submit', function(e) {
  e.preventDefault();
  var user = document.getElementById('login-user').value;
  var pass = document.getElementById('login-pass').value;
  var errEl = document.getElementById('login-error');
  var btn = this.querySelector('.login-btn');
  btn.textContent = 'Entrando...';
  btn.disabled = true;
  fetch('/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({username: user, password: pass})
  }).then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.status === 'ok') {
      window.location.href = '/';
    } else {
      errEl.style.display = 'block';
      btn.textContent = 'Entrar';
      btn.disabled = false;
    }
  }).catch(function() {
    errEl.style.display = 'block';
    btn.textContent = 'Entrar';
    btn.disabled = false;
  });
});
</script>
</body>
</html>
"""

# ─── Auth endpoints ───────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    user = authenticate(req.username, req.password)
    if not user:
        return JSONResponse({"status": "error", "message": "Credenciais inválidas"}, status_code=401)
    token = create_session(user["id"])
    response = JSONResponse({"status": "ok", "user": user})
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400*7)
    return response

@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session")
    if token:
        destroy_session(token)
    response = JSONResponse({"status": "ok"})
    response.delete_cookie("session")
    return response

@app.get("/api/auth/me")
def auth_me(request: Request):
    user = _get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return {"status": "ok", "user": user, "role_info": ROLES.get(user["role"])}

@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page():
    return HTMLResponse(content=LOGIN_HTML)

# ─── User Management endpoints ────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    name: str = ""
    email: str = ""
    password: str
    role: str = "viewer"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None

@app.get("/api/users")
def list_users(request: Request):
    user = _get_current_user(request)
    if not user or not has_permission(user, "manage_users"):
        raise HTTPException(status_code=403, detail="Sem permissão")
    return {"status": "ok", "users": get_all_users(), "roles": ROLES}

@app.post("/api/users")
def add_user(data: UserCreate, request: Request):
    user = _get_current_user(request)
    if not user or not has_permission(user, "manage_users"):
        raise HTTPException(status_code=403, detail="Sem permissão")
    new_user = create_user(data.model_dump())
    return {"status": "ok", "user": new_user}

@app.put("/api/users/{user_id}")
def edit_user(user_id: int, data: UserUpdate, request: Request):
    user = _get_current_user(request)
    if not user or not has_permission(user, "manage_users"):
        raise HTTPException(status_code=403, detail="Sem permissão")
    updated = update_user(user_id, {k: v for k, v in data.model_dump().items() if v is not None})
    if not updated:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"status": "ok", "user": updated}

@app.delete("/api/users/{user_id}")
def remove_user(user_id: int, request: Request):
    user = _get_current_user(request)
    if not user or not has_permission(user, "manage_users"):
        raise HTTPException(status_code=403, detail="Sem permissão")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não pode excluir a si mesmo")
    if not delete_user(user_id):
        raise HTTPException(status_code=400, detail="Não pode excluir o último admin")
    return {"status": "ok"}


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
<link rel="stylesheet" href="/static/css/style.css?v=20260422"/>
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
      <a class="sidebar-item" data-page="roadmap" href="#roadmap">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>
        <span>Roadmap</span>
      </a>
      <a class="sidebar-item" data-page="estrategia" href="#estrategia">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20h20M6 20V10M12 20V4M18 20v-6"/></svg>
        <span>Estrat&eacute;gia</span>
      </a>
      <a class="sidebar-item" data-page="agentes" href="#agentes">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a2 2 0 110 4h-1.07A7.001 7.001 0 0113 23h-2a7.001 7.001 0 01-6.93-5H3a2 2 0 110-4h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z"/></svg>
        <span>Agentes IA</span>
        <span class="sidebar-badge">&middot; 7</span>
      </a>
      <a class="sidebar-item" data-page="vexia" href="#vexia">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
        <span>Vexia</span>
        <span class="sidebar-badge">&middot; 7</span>
      </a>

      <div class="sidebar-divider" style="margin-top: auto;"></div>

      <a class="sidebar-item" data-page="usuarios" href="#usuarios">
        <svg class="sidebar-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
        <span>Usu&aacute;rios</span>
      </a>
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
        <button class="btn btn--ghost" id="btn-logout" style="font-size:11px;color:var(--text-subtle)">Sair</button>
        <div class="topbar-avatar" id="topbar-avatar">CA</div>
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
            <span class="metric-value font-mono" id="metric-entrevistas">0</span>
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
                <div class="team-avatar">CS</div>
                <div class="team-info">
                  <span class="team-name">Carolina Stocche</span>
                  <span class="team-role">CEO</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">LK</div>
                <div class="team-info">
                  <span class="team-name">Leo Koki</span>
                  <span class="team-role">Analista de Dados</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">VA</div>
                <div class="team-info">
                  <span class="team-name">Val&eacute;ria Araujo</span>
                  <span class="team-role">Desenvolvedora</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">CA</div>
                <div class="team-info">
                  <span class="team-name">Cau&ecirc; Aguiar</span>
                  <span class="team-role">Desenvolvedor</span>
                </div>
              </div>
              <div class="team-member">
                <div class="team-avatar">IV</div>
                <div class="team-info">
                  <span class="team-name">Isabela Vannucchi</span>
                  <span class="team-role">PMO</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card-section">
          <h2 class="section-heading">Timeline do projeto</h2>
          <div class="timeline-simple" id="project-timeline">
            <div class="timeline-item timeline-item--done" data-tl-id="0" data-tl-status="done">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header-row">
                  <div>
                    <input type="text" class="timeline-date-input" placeholder="A definir" value="" data-tl-date />
                    <span class="timeline-label">Kickoff &amp; alinhamento</span>
                  </div>
                  <select class="tl-status-select font-mono" data-tl-select>
                    <option value="done" selected>Conclu&iacute;do</option>
                    <option value="active">Em andamento</option>
                    <option value="pending">Pendente</option>
                  </select>
                </div>
                <div class="timeline-detail" style="display:none">
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">DELIVERABLES</span>
                    <div class="timeline-checklist">
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Reuni&atilde;o de kickoff com diretoria</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Defini&ccedil;&atilde;o de escopo e pilares</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Cronograma aprovado</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Acesso a dados e sistemas concedido</label>
                    </div>
                  </div>
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">NOTAS</span>
                    <textarea class="tl-note-input" rows="2">Diretoria engajada. Prioridade confirmada pelo CEO. Budget aprovado para consultoria de 3 meses.</textarea>
                  </div>
                  <div class="tl-progress-row"><span class="tl-progress-text font-mono">4/4 conclu&iacute;dos</span></div>
                </div>
              </div>
            </div>

            <div class="timeline-item timeline-item--done" data-tl-id="1" data-tl-status="done">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header-row">
                  <div>
                    <input type="text" class="timeline-date-input" placeholder="A definir" value="" data-tl-date />
                    <span class="timeline-label">Entrevistas com stakeholders</span>
                  </div>
                  <select class="tl-status-select font-mono" data-tl-select>
                    <option value="done" selected>Conclu&iacute;do</option>
                    <option value="active">Em andamento</option>
                    <option value="pending">Pendente</option>
                  </select>
                </div>
                <div class="timeline-detail" style="display:none">
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">DELIVERABLES</span>
                    <div class="timeline-checklist">
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Entrevista Dir. Industrial (R. Mendes)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Entrevista Ger. Comercial (C. Pinheiro)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Entrevista Dir. TI (L. Torres)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Entrevista Coord. Qualidade (A. Farias)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Entrevista CFO (pendente)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Entrevista Ger. Log&iacute;stica (pendente)</label>
                    </div>
                  </div>
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">NOTAS</span>
                    <textarea class="tl-note-input" rows="2">4 de 6 entrevistas conclu&iacute;das. 2 pendentes por conflito de agenda.</textarea>
                  </div>
                  <div class="tl-progress-row"><span class="tl-progress-text font-mono">4/6 conclu&iacute;dos</span></div>
                </div>
              </div>
            </div>

            <div class="timeline-item timeline-item--active" data-tl-id="2" data-tl-status="active">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header-row">
                  <div>
                    <input type="text" class="timeline-date-input" placeholder="A definir" value="" data-tl-date />
                    <span class="timeline-label">An&aacute;lise e diagn&oacute;stico por pilar</span>
                  </div>
                  <select class="tl-status-select font-mono" data-tl-select>
                    <option value="done">Conclu&iacute;do</option>
                    <option value="active" selected>Em andamento</option>
                    <option value="pending">Pendente</option>
                  </select>
                </div>
                <div class="timeline-detail" style="display:none">
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">DELIVERABLES</span>
                    <div class="timeline-checklist">
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Processamento de entrevistas pela IA</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" checked /> Score preliminar por pilar</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Valida&ccedil;&atilde;o de scores com cliente</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Relat&oacute;rio de diagn&oacute;stico por pilar</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Benchmark vs setor t&ecirc;xtil (ABIT)</label>
                    </div>
                  </div>
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">NOTAS</span>
                    <textarea class="tl-note-input" rows="2">Score geral 1.9/5.0. Defasagem cr&iacute;tica em Sistemas &amp; Dados (1.5).</textarea>
                  </div>
                  <div class="tl-progress-row">
                    <span class="tl-progress-text font-mono">2/5 conclu&iacute;dos</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="timeline-item" data-tl-id="3" data-tl-status="pending">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header-row">
                  <div>
                    <input type="text" class="timeline-date-input" placeholder="A definir" value="" data-tl-date />
                    <span class="timeline-label">Gera&ccedil;&atilde;o de estrat&eacute;gia e roadmap</span>
                  </div>
                  <select class="tl-status-select font-mono" data-tl-select>
                    <option value="done">Conclu&iacute;do</option>
                    <option value="active">Em andamento</option>
                    <option value="pending" selected>Pendente</option>
                  </select>
                </div>
                <div class="timeline-detail" style="display:none">
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">DELIVERABLES</span>
                    <div class="timeline-checklist">
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Gera&ccedil;&atilde;o de estrat&eacute;gia via IA</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Prioriza&ccedil;&atilde;o de quick wins por ROI</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Business case por iniciativa</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Roadmap de transforma&ccedil;&atilde;o em 3 ondas</label>
                    </div>
                  </div>
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">NOTAS</span>
                    <textarea class="tl-note-input" rows="2" placeholder="Adicionar notas..."></textarea>
                  </div>
                  <div class="tl-progress-row"><span class="tl-progress-text font-mono">0/4 conclu&iacute;dos</span></div>
                </div>
              </div>
            </div>

            <div class="timeline-item" data-tl-id="4" data-tl-status="pending">
              <div class="timeline-marker"></div>
              <div class="timeline-content">
                <div class="timeline-header-row">
                  <div>
                    <input type="text" class="timeline-date-input" placeholder="A definir" value="" data-tl-date />
                    <span class="timeline-label">Apresenta&ccedil;&atilde;o executiva</span>
                  </div>
                  <select class="tl-status-select font-mono" data-tl-select>
                    <option value="done">Conclu&iacute;do</option>
                    <option value="active">Em andamento</option>
                    <option value="pending" selected>Pendente</option>
                  </select>
                </div>
                <div class="timeline-detail" style="display:none">
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">DELIVERABLES</span>
                    <div class="timeline-checklist">
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Deck executivo para diretoria</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Relat&oacute;rio final de diagn&oacute;stico</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Sess&atilde;o de apresenta&ccedil;&atilde;o (2h)</label>
                      <label class="tl-check-label"><input type="checkbox" class="tl-checkbox" /> Handoff e pr&oacute;ximos passos</label>
                    </div>
                  </div>
                  <div class="timeline-detail-section">
                    <span class="timeline-detail-label">NOTAS</span>
                    <textarea class="tl-note-input" rows="2" placeholder="Adicionar notas..."></textarea>
                  </div>
                  <div class="tl-progress-row"><span class="tl-progress-text font-mono">0/4 conclu&iacute;dos</span></div>
                </div>
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
            <button class="btn btn--primary" id="btn-nova-entrevista">Nova Entrevista</button>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Filtro por area -->
        <h2 class="section-heading" style="margin-bottom: var(--space-5);">Entrevistas por &Aacute;rea</h2>
        <div class="area-tabs" id="area-tabs">
          <button class="area-tab active" data-area-filter="all">Todas</button>
          <button class="area-tab" data-area-filter="supply-chain">Supply Chain</button>
          <button class="area-tab" data-area-filter="producao">Produ&ccedil;&atilde;o</button>
          <button class="area-tab" data-area-filter="comercial">Comercial</button>
          <button class="area-tab" data-area-filter="logistica">Log&iacute;stica</button>
          <button class="area-tab" data-area-filter="ti">TI</button>
          <button class="area-tab" data-area-filter="financeiro">Financeiro</button>
          <button class="area-tab" data-area-filter="qualidade">Qualidade</button>
          <button class="area-tab" data-area-filter="compras">Compras</button>
          <button class="area-tab" data-area-filter="rh">RH</button>
          <button class="area-tab" data-area-filter="diretoria">Diretoria</button>
        </div>

        <!-- Entrevistados -->
        <h2 class="section-heading" style="margin-top: var(--space-5); margin-bottom: var(--space-5);">Entrevistas Cadastradas</h2>
        <div class="interview-grid" id="interview-grid">
        </div>

        <div class="empty-state" id="interview-empty">
          <svg class="empty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
          <p class="empty-text">Nenhuma entrevista cadastrada. Clique em "Nova Entrevista" para come&ccedil;ar.</p>
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
            <tbody id="coverage-tbody">
              <tr>
                <td class="coverage-name" colspan="6" style="text-align: center; color: var(--text-subtle); font-style: italic;">Adicione entrevistas para popular o mapa</td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <!-- ══ PAGE: ROADMAP ══ -->
      <div class="page" id="page-roadmap" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Roadmap</h1>
            <p class="page-subtitle">Plano de transforma&ccedil;&atilde;o estrat&eacute;gica por &aacute;rea</p>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Area selector -->
        <div style="margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-3)">
          <label class="form-label" style="margin:0; white-space:nowrap">&Aacute;rea:</label>
          <select class="form-input form-select" id="roadmap-area-select" style="max-width: 320px">
            <option value="">Selecione a &aacute;rea...</option>
            <option value="supply-chain">Supply Chain</option>
            <option value="producao">Produ&ccedil;&atilde;o / PCP</option>
            <option value="comercial">Comercial / Vendas</option>
            <option value="logistica">Log&iacute;stica</option>
            <option value="ti">Tecnologia / TI</option>
            <option value="financeiro">Financeiro / Controladoria</option>
            <option value="qualidade">Qualidade</option>
            <option value="compras">Compras / Procurement</option>
            <option value="rh">RH / Pessoas</option>
            <option value="diretoria">Diretoria Geral</option>
          </select>
        </div>

        <!-- Roadmap content (dynamic) -->
        <div id="roadmap-content">
          <div class="empty-state"><p class="empty-text">Execute o pipeline de uma &aacute;rea para gerar o roadmap (agente ATLAS)</p></div>
        </div>

      </div>

      <!-- ══ PAGE: ESTRATÉGIA ══ -->
      <div class="page" id="page-estrategia" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Estrat&eacute;gia</h1>
            <p class="page-subtitle">Roadmap estrat&eacute;gico, t&aacute;tico e automa&ccedil;&atilde;o por &aacute;rea</p>
          </div>
          <div class="page-header-actions">
            <button class="btn btn--ghost" id="btn-gerar-estrategia">&#9655; Gerar estrat&eacute;gia</button>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Area selector -->
        <div style="margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-3)">
          <label class="form-label" style="margin:0; white-space:nowrap">&Aacute;rea:</label>
          <select class="form-input form-select" id="strategy-area-select" style="max-width: 320px">
            <option value="">Selecione a &aacute;rea...</option>
            <option value="supply-chain">Supply Chain</option>
            <option value="producao">Produ&ccedil;&atilde;o / PCP</option>
            <option value="comercial">Comercial / Vendas</option>
            <option value="logistica">Log&iacute;stica</option>
            <option value="ti">Tecnologia / TI</option>
            <option value="financeiro">Financeiro / Controladoria</option>
            <option value="qualidade">Qualidade</option>
            <option value="compras">Compras / Procurement</option>
            <option value="rh">RH / Pessoas</option>
            <option value="diretoria">Diretoria Geral</option>
          </select>
        </div>

        <!-- Strategy tabs -->
        <div class="tabs" id="strategy-tabs" style="display:none">
          <button class="tab active" data-stab="macro">Roadmap Macro</button>
          <button class="tab" data-stab="tatico">Roadmap T&aacute;tico</button>
          <button class="tab" data-stab="automacao">Automa&ccedil;&atilde;o</button>
        </div>

        <!-- Strategy content -->
        <div id="strategy-content">
          <div class="stab-content" id="stab-macro">
            <div class="empty-state"><p class="empty-text">Selecione uma &aacute;rea e clique em &ldquo;Gerar estrat&eacute;gia&rdquo;</p></div>
          </div>
          <div class="stab-content" id="stab-tatico" style="display:none">
            <div class="empty-state"><p class="empty-text">Roadmap t&aacute;tico ser&aacute; gerado junto com a estrat&eacute;gia</p></div>
          </div>
          <div class="stab-content" id="stab-automacao" style="display:none">
            <div class="empty-state"><p class="empty-text">Estrat&eacute;gia de automa&ccedil;&atilde;o ser&aacute; gerada junto com a estrat&eacute;gia</p></div>
          </div>
        </div>

      </div>

      <!-- ══ PAGE: AGENTES IA ══ -->
      <div class="page" id="page-agentes" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Agentes IA</h1>
            <p class="page-subtitle">8 agentes especializados em consultoria estrat&eacute;gica de supply chain</p>
          </div>
          <div class="page-header-actions">
            <span class="page-counter font-mono">8 agentes &middot; Claude API</span>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Agent Grid -->
        <div class="agent-grid" id="agent-grid">

          <div class="agent-card" data-agent="aria">
            <div class="agent-card-header">
              <span class="agent-name font-mono">ARIA</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">Diagn&oacute;stico de Maturidade</span>
            <p class="agent-desc">Avalia maturidade operacional usando CMMI adaptado para supply chain. Scoring 1&ndash;5 por pilar.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">CMMI</span>
              <span class="agent-fw">SCOR</span>
              <span class="agent-fw">Gartner</span>
            </div>
          </div>

          <div class="agent-card" data-agent="strategos">
            <div class="agent-card-header">
              <span class="agent-name font-mono">STRATEGOS</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">An&aacute;lise de Gaps Estrat&eacute;gicos</span>
            <p class="agent-desc">Identifica gaps entre estado atual e alvo com McKinsey 7S e princ&iacute;pios MECE. Mapeia interdepend&ecirc;ncias.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">McKinsey 7S</span>
              <span class="agent-fw">MECE</span>
              <span class="agent-fw">Porter</span>
            </div>
          </div>

          <div class="agent-card" data-agent="sentinel">
            <div class="agent-card-header">
              <span class="agent-name font-mono">SENTINEL</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">Avalia&ccedil;&atilde;o de Riscos</span>
            <p class="agent-desc">Matriz de riscos probabilidade&times;impacto. Planos de mitiga&ccedil;&atilde;o com respons&aacute;veis e prazos.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">ISO 31000</span>
              <span class="agent-fw">COSO ERM</span>
              <span class="agent-fw">Bow-Tie</span>
            </div>
          </div>

          <div class="agent-card" data-agent="nexus">
            <div class="agent-card-header">
              <span class="agent-name font-mono">NEXUS</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">Benchmark &amp; Intelig&ecirc;ncia de Mercado</span>
            <p class="agent-desc">Compara performance com benchmarks ABIT/IEMI e best practices globais do setor t&ecirc;xtil.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">Benchmarking</span>
              <span class="agent-fw">Best Practices</span>
              <span class="agent-fw">CI</span>
            </div>
          </div>

          <div class="agent-card" data-agent="catalyst">
            <div class="agent-card-header">
              <span class="agent-name font-mono">CATALYST</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">Business Case &amp; ROI</span>
            <p class="agent-desc">Business cases com NPV, payback e IRR. Modela 3 cen&aacute;rios com an&aacute;lise de sensibilidade.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">DCF/NPV</span>
              <span class="agent-fw">IRR</span>
              <span class="agent-fw">Monte Carlo</span>
            </div>
          </div>

          <div class="agent-card" data-agent="prism">
            <div class="agent-card-header">
              <span class="agent-name font-mono">PRISM</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">An&aacute;lise de Entrevistas</span>
            <p class="agent-desc">Extrai temas, sentimentos, contradi&ccedil;&otilde;es e insights n&atilde;o-&oacute;bvios das transcri&ccedil;&otilde;es de entrevistas.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">Grounded Theory</span>
              <span class="agent-fw">Thematic</span>
              <span class="agent-fw">NLP</span>
            </div>
          </div>

          <div class="agent-card" data-agent="atlas">
            <div class="agent-card-header">
              <span class="agent-name font-mono">ATLAS</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">Roadmap &amp; Transforma&ccedil;&atilde;o</span>
            <p class="agent-desc">Roadmaps em ondas com depend&ecirc;ncias, milestones, OKRs e plano de change management.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">Wave Planning</span>
              <span class="agent-fw">OKR</span>
              <span class="agent-fw">Kotter</span>
            </div>
          </div>

          <div class="agent-card" data-agent="synapse">
            <div class="agent-card-header">
              <span class="agent-name font-mono">SYNAPSE</span>
              <span class="agent-status">Pronto</span>
            </div>
            <span class="agent-role">An&aacute;lise Integrada do Workflow</span>
            <p class="agent-desc">An&aacute;lise consolidada de todo o processo da consultoria, cruzando diagn&oacute;stico, gaps, riscos, benchmarks e roadmap numa vis&atilde;o hol&iacute;stica.</p>
            <div class="agent-frameworks">
              <span class="agent-fw">Balanced Scorecard</span>
              <span class="agent-fw">Systems Thinking</span>
              <span class="agent-fw">PDCA</span>
            </div>
          </div>

        </div>

        <!-- Agent Chat Panel (hidden by default) -->
        <div class="agent-chat-panel" id="agent-chat-panel" style="display:none">
          <div class="agent-chat-header">
            <button class="btn btn--ghost agent-back-btn" id="agent-back-btn">&larr; Voltar</button>
            <div class="agent-chat-title">
              <span class="agent-chat-name font-mono" id="agent-chat-name">ARIA</span>
              <span class="agent-chat-role" id="agent-chat-role">Diagn&oacute;stico de Maturidade</span>
            </div>
          </div>
          <div class="agent-chat-messages" id="agent-chat-messages">
            <div class="agent-welcome">
              <p class="body-text">Envie uma mensagem para iniciar a an&aacute;lise. O agente usar&aacute; o contexto do projeto Santista S.A. automaticamente.</p>
            </div>
          </div>
          <div class="agent-chat-input-area">
            <textarea class="agent-input" id="agent-input" rows="3" placeholder="Ex: Analise o pilar de Sistemas &amp; Dados e sugira as 3 a&ccedil;&otilde;es mais urgentes..."></textarea>
            <button class="btn btn--primary agent-send-btn" id="agent-send-btn">Enviar</button>
          </div>
        </div>
      </div>

      <!-- ══ PAGE: USUARIOS ══ -->
      <div class="page" id="page-usuarios" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Usu&aacute;rios</h1>
            <p class="page-subtitle">Gerenciamento de acessos e permiss&otilde;es</p>
          </div>
          <div class="page-header-actions">
            <button class="btn btn--primary" id="btn-novo-usuario">Novo Usu&aacute;rio</button>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- Roles legend -->
        <div class="roles-legend">
          <span class="role-badge role-badge--admin font-mono">ADMIN</span> Acesso total, gerencia usu&aacute;rios
          <span class="role-badge role-badge--editor font-mono">EDITOR</span> Cria e edita dados, roda agentes
          <span class="role-badge role-badge--viewer font-mono">VIEWER</span> Somente leitura
        </div>

        <!-- Users table -->
        <div class="users-table-wrap">
          <table class="users-table" id="users-table">
            <thead>
              <tr>
                <th>Usu&aacute;rio</th>
                <th>Nome</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>A&ccedil;&otilde;es</th>
              </tr>
            </thead>
            <tbody id="users-tbody">
              <tr><td colspan="6" style="text-align:center;color:var(--text-subtle)">Carregando...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ══ PAGE: VEXIA ══ -->
      <div class="page" id="page-vexia" style="display:none">
        <div class="page-header">
          <div class="page-header-text">
            <h1 class="page-title">Vexia &mdash; BPO &amp; Consultoria</h1>
            <p class="page-subtitle">An&aacute;lise consolidada dos processos de BPO operados pela Vexia para a Santista</p>
          </div>
          <div class="page-header-actions">
            <span class="page-counter font-mono">7 &aacute;reas mapeadas &middot; 300 colaboradores Vexia</span>
          </div>
        </div>
        <div class="page-header-divider"></div>

        <!-- RESUMO EXECUTIVO -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Resumo Executivo</h2>
          </div>
          <div class="card-section" style="line-height:1.7">
            <p>A <strong>Vexia</strong> (300 colaboradores) &eacute; especialista em BPO e ITO, operando &aacute;reas cr&iacute;ticas da Santista: <strong>Fiscal, Suprimentos, Financeiro, RH/Folha, Contabilidade, Compliance e Tecnologia</strong>. A Santista contrata BPO full, exceto an&aacute;lise de cr&eacute;dito e compras (internas).</p>
            <p style="margin-top:var(--space-3)">Os principais desafios envolvem <strong>processos arcaicos</strong> (especialmente fiscal), <strong>alta depend&ecirc;ncia de documentos f&iacute;sicos</strong>, baixa integra&ccedil;&atilde;o sist&ecirc;mica e elevado grau de manualidade. A falta de controle documental eficiente e aus&ecirc;ncia de procedimentos claros impacta qualidade e conformidade, gerando <strong>riscos fiscais e financeiros</strong>.</p>
          </div>
        </div>

        <div class="page-header-divider" style="margin-top:var(--space-6)"></div>

        <!-- HIGHLIGHTS CARDS -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Highlights</h2>
            <p class="card-subtitle">Vis&atilde;o consolidada dos principais pontos cr&iacute;ticos identificados</p>
          </div>
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap:var(--space-4)">

            <div class="card-section" style="border-left:4px solid var(--danger); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Fiscal</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Processo arcaico com uso intenso de papel (DANF, CTE), documentos f&iacute;sicos escaneados e enviados por e-mail.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Risco elevado de erros e exposi&ccedil;&atilde;o fiscal</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Digitaliza&ccedil;&atilde;o e automatiza&ccedil;&atilde;o</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--danger); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Gest&atilde;o Documental</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Falta de sistema para gest&atilde;o de NFs e docs fiscais. <strong>~1.300 notas n&atilde;o digitadas/ano.</strong></p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Inconsist&ecirc;ncias fiscais e financeiras</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Plataforma robusta e controle de fluxo</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--warning, #e6a817); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Integra&ccedil;&atilde;o de Sistemas</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Baixa integra&ccedil;&atilde;o entre PeopleSoft, Senior, Request e GSEC. Uso extensivo de planilhas e controles manuais.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Riscos operacionais e baixa efici&ecirc;ncia</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Automa&ccedil;&atilde;o, integra&ccedil;&atilde;o e RPA</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--warning, #e6a817); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Financeiro</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Pagamentos com SLA 2 dias, mas <strong>10% manuais</strong> geram inconsist&ecirc;ncias. Falta gest&atilde;o ativa de contas a pagar.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Pagamentos indevidos e atrasos</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Automa&ccedil;&atilde;o e valida&ccedil;&atilde;o</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--warning, #e6a817); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Contas a Receber</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Estruturado via ERP, mas desafios em concilia&ccedil;&atilde;o e gest&atilde;o de inadimpl&ecirc;ncia. Acordos informais sem controle.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Dificuldade na gest&atilde;o financeira</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">PDD por t&iacute;tulo e concilia&ccedil;&otilde;es auto</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--danger); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">RH / Folha</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">HR360 e Request com integra&ccedil;&atilde;o manual ao Senior. <strong>193 afastados</strong> com descontrole financeiro.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Rescis&otilde;es cr&iacute;ticas, afastados sem controle</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Integra&ccedil;&atilde;o e workflows formais</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--warning, #e6a817); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Compliance &amp; Auditoria</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Auditorias eletr&ocirc;nicas contratadas mas pouco utilizadas. Visibilidade limitada e processos manuais.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">N&atilde;o conformidade fiscal/trabalhista</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Auditoria eletr&ocirc;nica</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--danger); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Seguran&ccedil;a</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Riscos de fraude em cobran&ccedil;as (2&ordf; via boletos, golpes via WhatsApp). Vulnerabilidades em comunica&ccedil;&atilde;o.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Exposi&ccedil;&atilde;o a fraudes e perdas</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Controles antifraude e alertas</span>
              </div>
            </div>

            <div class="card-section" style="border-left:4px solid var(--warning, #e6a817); padding:var(--space-4)">
              <h3 style="margin:0 0 var(--space-2) 0; font-size:0.95rem; color:var(--accent)">Gest&atilde;o de Fornecedores</h3>
              <p style="font-size:0.88rem; line-height:1.6; margin:0 0 var(--space-3) 0">Cadastro e habilita&ccedil;&atilde;o descentralizados e manuais, impactando controle fiscal e operacional.</p>
              <div style="display:flex; gap:var(--space-3); font-size:0.82rem">
                <span style="background:rgba(220,53,69,0.1); color:var(--danger); padding:2px 8px; border-radius:var(--radius-sm)">Inconsist&ecirc;ncias e erros fiscais</span>
                <span style="background:rgba(40,167,69,0.1); color:var(--success); padding:2px 8px; border-radius:var(--radius-sm)">Centralizar e automatizar</span>
              </div>
            </div>

          </div>
        </div>

        <div class="page-header-divider" style="margin-top:var(--space-6)"></div>

        <!-- DETALHAMENTO POR AREAS -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Detalhamento por &Aacute;rea</h2>
            <p class="card-subtitle">Processo atual, problemas identificados e oportunidades de melhoria</p>
          </div>

          <!-- FILTRO DE AREAS -->
          <div class="area-filter-bar" id="vexia-area-filter" style="display:flex; gap:var(--space-2); flex-wrap:wrap; margin-bottom:var(--space-5)">
            <button class="area-tab active" data-vexia-area="all">Todas</button>
            <button class="area-tab" data-vexia-area="fiscal">Fiscal</button>
            <button class="area-tab" data-vexia-area="suprimentos">Suprimentos</button>
            <button class="area-tab" data-vexia-area="financeiro">Financeiro</button>
            <button class="area-tab" data-vexia-area="rh">RH / Folha</button>
            <button class="area-tab" data-vexia-area="contabilidade">Contabilidade</button>
            <button class="area-tab" data-vexia-area="compliance">Compliance</button>
            <button class="area-tab" data-vexia-area="tecnologia">Tecnologia</button>
          </div>

          <!-- 3.1 FISCAL -->
          <div class="card-section vexia-area-card" data-vexia-area="fiscal" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">FISCAL</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Processos predominantemente manuais e f&iacute;sicos para controle fiscal, principalmente recebimento de materiais com DANF escaneados e enviados por e-mail</li>
                <li>Confer&ecirc;ncia f&iacute;sica pela Santista, lan&ccedil;amento e registro pela Vexia &mdash; documentos frequentemente incompletos</li>
                <li>Aus&ecirc;ncia de sistema dedicado para gest&atilde;o de NFs; ~1.300 notas n&atilde;o digitadas ou auditadas por ano</li>
                <li>Falta de responsabilidade clara entre &aacute;reas para gest&atilde;o de documentos fiscais</li>
                <li>Problemas com tributa&ccedil;&atilde;o, erros na emiss&atilde;o e baixa intelig&ecirc;ncia para bloqueio de erros</li>
                <li>CTEs de entrada n&atilde;o reconhecidos em tempo h&aacute;bil &mdash; exposi&ccedil;&atilde;o fiscal e cont&aacute;bil</li>
                <li>Devolu&ccedil;&otilde;es, adiantamentos e compras com cart&atilde;o desvinculados e manuais</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Processo muito manual e descentralizado</li>
                <li>Falta de padroniza&ccedil;&atilde;o e defini&ccedil;&atilde;o clara de processos e rotas para NFs</li>
                <li>Exposi&ccedil;&atilde;o a riscos fiscais e atrasos no pagamento</li>
                <li>Documentos fiscais e financeiros que n&atilde;o &ldquo;conversam&rdquo; entre si</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Digitaliza&ccedil;&atilde;o e automa&ccedil;&atilde;o do processo fiscal</li>
                <li>Plataforma &uacute;nica para gest&atilde;o de documentos fiscais</li>
                <li>Intelig&ecirc;ncia fiscal para valida&ccedil;&atilde;o autom&aacute;tica</li>
                <li>Redesenho ponta a ponta para CTE e fretes</li>
              </ul>
            </details>
          </div>

          <!-- 3.2 SUPRIMENTOS -->
          <div class="card-section vexia-area-card" data-vexia-area="suprimentos" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">SUPRIMENTOS</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Recebimentos descentralizados, m&uacute;ltiplas &aacute;reas enviando documentos &agrave; Vexia</li>
                <li>Cadastro e habilita&ccedil;&atilde;o de fornecedores pelo Suprimentos da Santista, controle fragmentado</li>
                <li>Falta de integra&ccedil;&atilde;o entre ordens de compra, cadastro de fornecedores e contas cont&aacute;beis</li>
                <li>Devolu&ccedil;&otilde;es, adiantamentos e compras com cart&atilde;o desvinculados e manuais</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Falta de controle e padroniza&ccedil;&atilde;o</li>
                <li>Risco operacional e fiscal devido a processos manuais</li>
                <li>Exposi&ccedil;&atilde;o por falta de visibilidade nas opera&ccedil;&otilde;es</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Centraliza&ccedil;&atilde;o e automatiza&ccedil;&atilde;o do cadastro e gest&atilde;o de fornecedores</li>
                <li>Integra&ccedil;&atilde;o dos processos de compras, recebimentos e pagamentos</li>
                <li>Implementa&ccedil;&atilde;o de workflows e controles automatizados</li>
              </ul>
            </details>
          </div>

          <!-- 3.3 FINANCEIRO -->
          <div class="card-section vexia-area-card" data-vexia-area="financeiro" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">FINANCEIRO</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Vexia gerencia contas a pagar e contas a receber da Santista</li>
                <li>Pagamentos majoritariamente via arquivos banc&aacute;rios eletr&ocirc;nicos (SLA 2 dias)</li>
                <li>10% de pagamentos manuais &mdash; fonte de inconsist&ecirc;ncias</li>
                <li>Concilia&ccedil;&atilde;o banc&aacute;ria e fluxos de caixa parcialmente automatizados, uso intenso de planilhas</li>
                <li>Carteira de receb&iacute;veis com acordos comerciais complexos, sem controle de PDD por t&iacute;tulo</li>
                <li>Gest&atilde;o de inadimpl&ecirc;ncia manual e complexa, baixa automa&ccedil;&atilde;o</li>
                <li>Pagamento de mat&eacute;rias-primas (algod&atilde;o) com descompassos fiscal/operacional</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Falta de gest&atilde;o ativa de contas a pagar (apenas pagamento do aprovado)</li>
                <li>Baixa visibilidade e controle em processos manuais</li>
                <li>Concilia&ccedil;&otilde;es e contabiliza&ccedil;&otilde;es complexas e demoradas</li>
                <li>Riscos de pagamento indevido e atrasos</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Controle rigoroso e gest&atilde;o completa de contas a pagar</li>
                <li>Automatizar concilia&ccedil;&otilde;es e controle de inadimpl&ecirc;ncia</li>
                <li>Integra&ccedil;&atilde;o entre sistemas financeiros e fiscais</li>
              </ul>
            </details>
          </div>

          <!-- 3.4 RH / FOLHA -->
          <div class="card-section vexia-area-card" data-vexia-area="rh" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">RH / FOLHA DE PAGAMENTO</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Todos os processos de folha e benef&iacute;cios transacionados pela Vexia</li>
                <li>Admiss&atilde;o digital via <strong>HR360</strong> (sistema Vexia com OCR)</li>
                <li>Demandas gerenciadas via plataforma <strong>Request</strong> com SLA definidos</li>
                <li>Cadastro e manuten&ccedil;&atilde;o cadastral manuais no sistema <strong>Senior</strong></li>
                <li>F&eacute;rias, rescis&otilde;es, c&aacute;lculo de folha e pagamentos pela Vexia (incl. emiss&atilde;o banc&aacute;ria e integra&ccedil;&atilde;o cont&aacute;bil)</li>
                <li>Controle de ponto gerenciado pela Santista, integra&ccedil;&atilde;o pela Vexia</li>
                <li>Apura&ccedil;&atilde;o e transmiss&atilde;o de encargos/impostos pela Vexia (E-Social, INSS, FGTS)</li>
                <li>Gest&atilde;o de afastados e benef&iacute;cios manual &mdash; 193 afastados ativos</li>
                <li>Volume: ~1.661 ativos, m&eacute;dia 65 admiss&otilde;es e 60 rescis&otilde;es/m&ecirc;s, R$13,5M movimentados/m&ecirc;s</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Integra&ccedil;&atilde;o HR360 &rarr; Senior &eacute; manual (n&atilde;o integrado)</li>
                <li>Aus&ecirc;ncia de workflow formal para aprova&ccedil;&atilde;o de descontos e reembolsos</li>
                <li>Fragilidade na gest&atilde;o de afastados &mdash; descontrole financeiro (plano m&eacute;dico sem reembolso, farm&aacute;cia)</li>
                <li>Rescis&atilde;o: processo cr&iacute;tico, prazo curto (10 dias), alto risco de multas</li>
                <li>Admiss&otilde;es fora do prazo por urg&ecirc;ncia da produ&ccedil;&atilde;o + cancelamentos frequentes</li>
                <li>Saldo devedor de funcion&aacute;rios demitidos n&atilde;o descontado na rescis&atilde;o &mdash; perdas financeiras</li>
                <li>Pend&ecirc;ncias cont&aacute;beis entre folha e financeiro n&atilde;o rastreadas</li>
                <li>Gestores sem visibilidade do custo de m&atilde;o de obra do centro de custo</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Automa&ccedil;&atilde;o da integra&ccedil;&atilde;o entre plataformas de RH</li>
                <li>Workflows formais para reembolsos e descontos</li>
                <li>Gest&atilde;o de afastados e benef&iacute;cios para minimizar perdas financeiras</li>
                <li>Otimiza&ccedil;&atilde;o de admiss&atilde;o e rescis&atilde;o (RPA para kit autom&aacute;tico)</li>
                <li>Visibilidade de custos de m&atilde;o de obra para gestores</li>
              </ul>
            </details>
          </div>

          <!-- 3.5 CONTABILIDADE -->
          <div class="card-section vexia-area-card" data-vexia-area="contabilidade" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">CONTABILIDADE</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Lan&ccedil;amentos cont&aacute;beis, fechamento e provis&otilde;es majoritariamente manuais</li>
                <li>Concilia&ccedil;&otilde;es com planilhas e e-mails, baixa automa&ccedil;&atilde;o</li>
                <li>Integra&ccedil;&atilde;o com PeopleSoft existe mas limitada; muitos lan&ccedil;amentos manuais</li>
                <li>Controle de PDD por t&iacute;tulo inexistente</li>
                <li>Opera&ccedil;&otilde;es internacionais (Argentina, energia) contabilizadas manualmente</li>
                <li>Relat&oacute;rios gerenciais em Excel, pouca gera&ccedil;&atilde;o autom&aacute;tica pelo ERP</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Alta depend&ecirc;ncia de processos manuais, risco de erros e atrasos</li>
                <li>Despadroniza&ccedil;&atilde;o e baixa efici&ecirc;ncia</li>
                <li>Falta de ferramentas automatizadas para concilia&ccedil;&atilde;o e controle fiscal</li>
                <li>Limita&ccedil;&otilde;es do ERP que impactam qualidade do controle</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Parametriza&ccedil;&otilde;es e automa&ccedil;&otilde;es para reduzir lan&ccedil;amentos manuais</li>
                <li>Ferramentas de auditoria e controle fiscal integradas</li>
                <li>Revis&atilde;o e atualiza&ccedil;&atilde;o do ERP</li>
              </ul>
            </details>
          </div>

          <!-- 3.6 COMPLIANCE -->
          <div class="card-section vexia-area-card" data-vexia-area="compliance" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">COMPLIANCE &amp; AUDITORIA</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Auditoria eletr&ocirc;nica (Revises) contratada, por&eacute;m pouco utilizada pela Santista</li>
                <li>Apura&ccedil;&atilde;o de impostos e obriga&ccedil;&otilde;es fiscais pela Vexia sem ampla visibilidade da Santista</li>
                <li>Encargos e multas por atrasos com pouca gest&atilde;o ativa</li>
                <li>Controle e gest&atilde;o de riscos (GRC) limitados, baseline de seguran&ccedil;a b&aacute;sico</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Falta de transpar&ecirc;ncia e integra&ccedil;&atilde;o no processo de auditoria</li>
                <li>Risco de n&atilde;o conformidade fiscal e trabalhista</li>
                <li>Processos manuais limitam efetividade do controle</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Expans&atilde;o do uso de auditorias eletr&ocirc;nicas</li>
                <li>Melhoria na comunica&ccedil;&atilde;o e visibilidade para a Santista</li>
                <li>Fortalecimento da governan&ccedil;a de riscos e compliance</li>
              </ul>
            </details>
          </div>

          <!-- 3.7 TECNOLOGIA -->
          <div class="card-section vexia-area-card" data-vexia-area="tecnologia" style="margin-bottom:var(--space-5)">
            <h3 class="card-label-heading" style="color:var(--accent)">SEGURAN&Ccedil;A &amp; TECNOLOGIA</h3>
            <details open>
              <summary style="cursor:pointer; font-weight:600; margin-bottom:var(--space-3)">Processo Atual</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Plataformas diversas: PeopleSoft, Senior, HR360, Request, Anfe, GSEC</li>
                <li>Automa&ccedil;&atilde;o parcial via RPA (extratos banc&aacute;rios, processos repetitivos)</li>
                <li>Riscos de fraude em cobran&ccedil;a (2&ordf; via boletos, golpes via WhatsApp)</li>
                <li>Estudo de tokens para substitui&ccedil;&atilde;o de FTA em processos financeiros</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--danger); margin-bottom:var(--space-3)">Problemas Identificados</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Falta de padroniza&ccedil;&atilde;o tecnol&oacute;gica e integra&ccedil;&atilde;o sist&ecirc;mica</li>
                <li>Vulnerabilidades em processos de cobran&ccedil;a e comunica&ccedil;&atilde;o</li>
                <li>Resist&ecirc;ncia &agrave; ado&ccedil;&atilde;o de novos procedimentos</li>
              </ul>
            </details>
            <details style="margin-top:var(--space-3)">
              <summary style="cursor:pointer; font-weight:600; color:var(--success); margin-bottom:var(--space-3)">Oportunidades</summary>
              <ul style="line-height:1.7; padding-left:var(--space-5)">
                <li>Solu&ccedil;&otilde;es de seguran&ccedil;a avan&ccedil;adas e controles antifraude</li>
                <li>Centraliza&ccedil;&atilde;o e integra&ccedil;&atilde;o tecnol&oacute;gica ampliada</li>
                <li>Capacita&ccedil;&atilde;o e gest&atilde;o da mudan&ccedil;a</li>
              </ul>
            </details>
          </div>
        </div>

        <div class="page-header-divider" style="margin-top:var(--space-6)"></div>

        <!-- DADOS OPERACIONAIS -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Dados Operacionais (Folha/RH)</h2>
            <p class="card-subtitle">Indicadores extra&iacute;dos da reuni&atilde;o com a equipe Vexia</p>
          </div>
          <div class="forms-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:var(--space-4)">
            <div class="card-section" style="text-align:center">
              <span class="card-label-heading">ATIVOS</span>
              <p style="font-size:2rem; font-weight:700; margin-top:var(--space-2)">1.661</p>
              <p class="card-subtitle">colaboradores ativos</p>
            </div>
            <div class="card-section" style="text-align:center">
              <span class="card-label-heading">AFASTADOS</span>
              <p style="font-size:2rem; font-weight:700; margin-top:var(--space-2); color:var(--danger)">193</p>
              <p class="card-subtitle">funcion&aacute;rios afastados</p>
            </div>
            <div class="card-section" style="text-align:center">
              <span class="card-label-heading">ADMISS&Otilde;ES/M&Ecirc;S</span>
              <p style="font-size:2rem; font-weight:700; margin-top:var(--space-2)">~65</p>
              <p class="card-subtitle">m&eacute;dia mensal</p>
            </div>
            <div class="card-section" style="text-align:center">
              <span class="card-label-heading">RESCIS&Otilde;ES/M&Ecirc;S</span>
              <p style="font-size:2rem; font-weight:700; margin-top:var(--space-2); color:var(--danger)">~60</p>
              <p class="card-subtitle">m&eacute;dia mensal</p>
            </div>
            <div class="card-section" style="text-align:center">
              <span class="card-label-heading">MOVIMENTA&Ccedil;&Atilde;O</span>
              <p style="font-size:2rem; font-weight:700; margin-top:var(--space-2)">R$13,5M</p>
              <p class="card-subtitle">m&eacute;dia/m&ecirc;s (2025)</p>
            </div>
          </div>
        </div>

        <div class="page-header-divider" style="margin-top:var(--space-6)"></div>

        <!-- SISTEMAS UTILIZADOS -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Ecossistema de Sistemas</h2>
            <p class="card-subtitle">Plataformas utilizadas na opera&ccedil;&atilde;o Vexia &harr; Santista</p>
          </div>
          <div class="forms-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:var(--space-3)">
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>PeopleSoft</strong><br><span class="card-subtitle">ERP / Financeiro / Cont&aacute;bil</span>
            </div>
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>Senior</strong><br><span class="card-subtitle">Folha / DP / Ponto</span>
            </div>
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>HR360</strong><br><span class="card-subtitle">Admiss&atilde;o Digital (OCR)</span>
            </div>
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>Request</strong><br><span class="card-subtitle">Gest&atilde;o de Demandas / SLA</span>
            </div>
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>Anfe</strong><br><span class="card-subtitle">Nota Fiscal Eletr&ocirc;nica</span>
            </div>
            <div class="card-section" style="text-align:center; padding:var(--space-4)">
              <strong>GSEC</strong><br><span class="card-subtitle">Seguran&ccedil;a / Controles</span>
            </div>
          </div>
        </div>

        <div class="page-header-divider" style="margin-top:var(--space-6)"></div>

        <!-- TRANSCRICAO -->
        <div class="forms-section">
          <div class="forms-section-header">
            <h2 class="section-heading">Transcri&ccedil;&atilde;o da Reuni&atilde;o</h2>
            <p class="card-subtitle">Reuni&atilde;o realizada na semana de 21/04/2026 com equipe Vexia</p>
          </div>
          <div class="card-section">
            <details>
              <summary style="cursor:pointer; font-weight:600">Clique para expandir a transcri&ccedil;&atilde;o completa</summary>
              <div id="vexia-transcricao" style="margin-top:var(--space-4); max-height:500px; overflow-y:auto; padding:var(--space-4); background:var(--surface-2); border-radius:var(--radius-md); font-size:0.9rem; line-height:1.8; white-space:pre-wrap"></div>
            </details>
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

<!-- ═══ MODAL: Nova Entrevista ═══ -->
<div class="modal-overlay" id="modal-entrevista" style="display:none">
  <div class="modal modal--wide">
    <div class="modal-header">
      <h2 class="modal-title">Nova Entrevista</h2>
      <button class="modal-close" id="modal-entrevista-close">&times;</button>
    </div>
    <form class="modal-form" id="form-entrevista">

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Entrevistador*</label>
          <input class="form-input" type="text" id="ent-entrevistador" placeholder="Ex: Joao Silva" required />
        </div>
        <div class="form-group">
          <label class="form-label">Nome do Entrevistado*</label>
          <input class="form-input" type="text" id="ent-nome" placeholder="Ex: Maria Souza" required />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Cargo*</label>
          <input class="form-input" type="text" id="ent-cargo" placeholder="Ex: Gerente de Operacoes" required />
        </div>
        <div class="form-group">
          <label class="form-label">&Aacute;rea / Departamento*</label>
          <select class="form-input form-select" id="ent-area" required>
            <option value="">Selecione a area...</option>
            <option value="supply-chain">Supply Chain</option>
            <option value="producao">Produ&ccedil;&atilde;o / PCP</option>
            <option value="comercial">Comercial / Vendas</option>
            <option value="logistica">Log&iacute;stica</option>
            <option value="ti">Tecnologia / TI</option>
            <option value="financeiro">Financeiro / Controladoria</option>
            <option value="qualidade">Qualidade</option>
            <option value="compras">Compras / Procurement</option>
            <option value="rh">RH / Pessoas</option>
            <option value="diretoria">Diretoria Geral</option>
          </select>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">N&iacute;vel Hier&aacute;rquico</label>
          <select class="form-input form-select" id="ent-nivel">
            <option value="gerencia">Ger&ecirc;ncia</option>
            <option value="diretoria">Diretoria</option>
            <option value="coordenacao">Coordena&ccedil;&atilde;o</option>
            <option value="supervisao">Supervis&atilde;o</option>
            <option value="analista">Analista / Especialista</option>
            <option value="c-level">C-Level</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Pilar do Assessment</label>
          <select class="form-input form-select" id="ent-pilar">
            <option value="supply-chain">Cadeia de Suprimentos</option>
            <option value="producao">Opera&ccedil;&otilde;es Industriais</option>
            <option value="comercial">Receita &amp; Growth</option>
            <option value="logistica">Opera&ccedil;&otilde;es Log&iacute;sticas</option>
            <option value="ti">Tecnologia &amp; Sistemas</option>
            <option value="financeiro">Finan&ccedil;as &amp; Performance</option>
            <option value="qualidade">Qualidade &amp; Compliance</option>
            <option value="compras">Suprimentos &amp; Aquisi&ccedil;&otilde;es</option>
            <option value="rh">Pessoas &amp; Cultura</option>
            <option value="diretoria">Estrat&eacute;gia &amp; Governan&ccedil;a</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Data da Entrevista*</label>
        <input class="form-input" type="date" id="ent-data" required style="max-width: 220px" />
      </div>

      <div class="form-group">
        <label class="form-label">Transcri&ccedil;&atilde;o da Entrevista</label>
        <textarea class="form-textarea" id="ent-transcricao" rows="4" placeholder="Cole aqui a transcricao completa da entrevista..."></textarea>
        <span class="form-hint">Adicionar a transcri&ccedil;&atilde;o habilita a an&aacute;lise por IA e altera o status para &ldquo;Conclu&iacute;da&rdquo;.</span>
      </div>

      <!-- Perguntas sugeridas por area -->
      <div class="form-questions" id="form-questions">
        <div class="form-questions-header" id="form-questions-toggle">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" stroke-width="2"><line x1="9" y1="18" x2="15" y2="18"/><line x1="10" y1="22" x2="14" y2="22"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14"/></svg>
          <span class="form-questions-title" id="form-questions-title">Selecione a &aacute;rea para ver perguntas sugeridas</span>
          <span class="form-questions-chevron" id="form-questions-chevron">&#8964;</span>
        </div>
        <div class="form-questions-list" id="form-questions-list"></div>
      </div>

      <!-- ia_ready é automático: ativado quando há transcrição -->

      <div class="modal-actions">
        <button type="button" class="btn btn--glass" id="modal-entrevista-cancel">Cancelar</button>
        <button type="submit" class="btn btn--primary">Salvar Entrevista</button>
      </div>
    </form>
  </div>
</div>

<!-- ═══ MODAL: Novo/Editar Usuario ═══ -->
<div class="modal-overlay" id="modal-usuario" style="display:none">
  <div class="modal">
    <div class="modal-header">
      <h2 class="modal-title" id="modal-usuario-title">Novo Usu&aacute;rio</h2>
      <button class="modal-close" id="modal-usuario-close">&times;</button>
    </div>
    <form class="modal-form" id="form-usuario">
      <input type="hidden" id="usr-edit-id" value="" />
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Usu&aacute;rio*</label>
          <input class="form-input" type="text" id="usr-username" placeholder="nome.sobrenome" required />
        </div>
        <div class="form-group">
          <label class="form-label">Nome completo</label>
          <input class="form-input" type="text" id="usr-name" placeholder="Nome Sobrenome" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Email</label>
          <input class="form-input" type="email" id="usr-email" placeholder="email@empresa.com" />
        </div>
        <div class="form-group">
          <label class="form-label">Role*</label>
          <select class="form-input form-select" id="usr-role" required>
            <option value="viewer">Visualizador</option>
            <option value="editor">Editor</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
      </div>
      <div class="form-group">
        <label class="form-label" id="usr-pass-label">Senha*</label>
        <input class="form-input" type="password" id="usr-password" placeholder="Min. 6 caracteres" />
      </div>
      <div class="modal-actions">
        <button type="button" class="btn btn--glass" id="modal-usuario-cancel">Cancelar</button>
        <button type="submit" class="btn btn--primary">Salvar</button>
      </div>
    </form>
  </div>
</div>

<script src="/static/js/app.js?v=20260428c"></script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def landing(request: Request):
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
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


# ─── AI Agents ───────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    message: str
    context: Optional[str] = ""

@app.get("/api/agents")
def list_agents():
    """Lista todos os agentes de IA disponíveis."""
    agents = get_all_agents()
    return {"status": "ok", "agents": [
        {k: v for k, v in a.items() if k != "system_prompt"}
        for a in agents
    ]}

@app.get("/api/agents/{agent_id}")
def agent_detail(agent_id: str):
    """Detalhe de um agente específico."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    return {"status": "ok", "agent": {k: v for k, v in agent.items() if k != "system_prompt"}}

@app.post("/api/agents/{agent_id}/run")
async def agent_run(agent_id: str, req: AgentRequest):
    """Executa um agente com uma mensagem do usuário."""
    logger.info(f"/api/agents/{agent_id}/run")

    # Injeta entrevistas e análises do banco como contexto automático
    ctx_parts = []
    if req.context:
        ctx_parts.append(req.context)

    interviews = get_interviews()
    ia_interviews = [i for i in interviews if i.get("transcript")]
    if ia_interviews:
        summaries = []
        for iv in ia_interviews:
            s = (f"- {iv['interviewee']} ({iv['role']}, {iv['department']}): "
                 f"{iv['transcript'][:500]}{'...' if len(iv.get('transcript','')) > 500 else ''}")
            if iv.get("analysis"):
                s += f"\n  ANÁLISE PRISM: {iv['analysis'][:500]}{'...' if len(iv.get('analysis','')) > 500 else ''}"
            summaries.append(s)
        ctx_parts.append(f"ENTREVISTAS SALVAS ({len(ia_interviews)}):\n" + "\n\n".join(summaries))

    analysis = get_analysis_results()
    if analysis:
        for key, val in analysis.items():
            content = val if isinstance(val, str) else (val.get("content", "") if isinstance(val, dict) else str(val))
            if content:
                ctx_parts.append(f"RESULTADO {key.upper()}:\n{content[:1000]}{'...' if len(content) > 1000 else ''}")

    full_context = "\n\n---\n\n".join(ctx_parts) if ctx_parts else ""
    result = await run_agent(agent_id, req.message, full_context)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", **result}


# ─── Data & Pipeline Endpoints ────────────────────────────────────────────────

class InterviewData(BaseModel):
    interviewer: str
    interviewee: str
    role: str
    department: str = ""
    level: str = ""
    pillar: str = ""
    date: str = ""
    transcript: str = ""
    ia_ready: bool = False

def _maybe_auto_trigger_pipeline(department: str, transcript: str):
    """Dispara o pipeline automaticamente quando a entrevista possui transcrição e área."""
    import asyncio
    if not (transcript and department):
        return
    status = get_pipeline_status()
    if status["running"]:
        logger.info(f"[auto-trigger] Pipeline já em execução, ignorando auto-trigger para {department}")
        return
    logger.info(f"[auto-trigger] Entrevista salva para área '{department}' — disparando pipeline + estratégia automaticamente")
    asyncio.create_task(run_area_pipeline(department))

@app.post("/api/interviews")
async def create_interview(data: InterviewData):
    """Salva uma entrevista no datastore e dispara pipeline automaticamente se houver transcrição."""
    payload = data.model_dump()
    # ia_ready é automático: True se tiver transcrição
    payload["ia_ready"] = bool(data.transcript and data.transcript.strip())
    interview = save_interview(payload)
    _maybe_auto_trigger_pipeline(data.department, data.transcript)
    return {"status": "ok", "interview": interview}

@app.get("/api/interviews")
def list_interviews():
    return {"status": "ok", "interviews": get_interviews()}

@app.put("/api/interviews/{interview_id}")
async def edit_interview(interview_id: int, data: InterviewData):
    """Atualiza uma entrevista existente e dispara pipeline automaticamente se houver transcrição."""
    payload = data.model_dump()
    payload["ia_ready"] = bool(data.transcript and data.transcript.strip())
    updated = update_interview(interview_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada")
    _maybe_auto_trigger_pipeline(data.department, data.transcript)
    return {"status": "ok", "interview": updated}

@app.delete("/api/interviews/{interview_id}")
def remove_interview(interview_id: int):
    """Remove uma entrevista."""
    if not delete_interview(interview_id):
        raise HTTPException(status_code=404, detail="Entrevista não encontrada")
    return {"status": "ok"}

@app.post("/api/pipeline/run")
async def trigger_pipeline(area: str = None):
    """Dispara o pipeline de análise. Se area for passada, roda só aquela área."""
    import asyncio
    status = get_pipeline_status()
    if status["running"]:
        return {"status": "already_running", "pipeline": status}
    if area:
        asyncio.create_task(run_area_pipeline(area))
        return {"status": "ok", "message": f"Pipeline iniciado para área: {area}"}
    asyncio.create_task(run_full_pipeline())
    return {"status": "ok", "message": "Pipeline iniciado para todas as áreas"}

@app.get("/api/pipeline/status")
def pipeline_status():
    return {"status": "ok", "pipeline": get_pipeline_status()}

@app.get("/api/analysis/areas")
def get_analysis_areas():
    """Retorna áreas que possuem resultados de análise."""
    return {"status": "ok", "areas": get_available_areas()}

@app.get("/api/analysis")
def get_analysis(area: str = None):
    """Retorna resultados de análise. Se area for passada, retorna só daquela área."""
    if area:
        return {
            "status": "ok",
            "area": area,
            "analysis": get_analysis_results_for_area(area),
        }
    return {
        "status": "ok",
        "analysis": get_analysis_results(),
        "areas": get_available_areas(),
    }


# ─── Strategy Endpoints ──────────────────────────────────────────────────────

@app.post("/api/strategy/run")
async def trigger_strategy(area: str = None):
    """Gera estratégia para uma área específica."""
    import asyncio
    if not area:
        return {"status": "error", "message": "Parâmetro 'area' é obrigatório"}
    status = get_pipeline_status()
    if status["running"]:
        return {"status": "already_running", "pipeline": status}
    asyncio.create_task(run_strategy_pipeline(area))
    return {"status": "ok", "message": f"Estratégia iniciada para área: {area}"}

@app.get("/api/strategy")
def get_strategy(area: str = None):
    """Retorna estratégia de uma área."""
    if not area:
        return {"status": "ok", "areas": get_available_areas()}
    results = get_analysis_results_for_area(area)
    return {
        "status": "ok",
        "area": area,
        "macro": results.get("strategy_macro", {}).get("content", "") if isinstance(results.get("strategy_macro"), dict) else results.get("strategy_macro", ""),
        "tatico": results.get("strategy_tatico", {}).get("content", "") if isinstance(results.get("strategy_tatico"), dict) else results.get("strategy_tatico", ""),
        "automacao": results.get("strategy_automacao", {}).get("content", "") if isinstance(results.get("strategy_automacao"), dict) else results.get("strategy_automacao", ""),
    }


# ─── Word Document Export/Import ──────────────────────────────────────────────

@app.get("/api/forms/export/{area}")
def export_form(area: str, interviewee: str = "", role: str = "", date: str = ""):
    """Exporta formulário de entrevista como .docx"""
    try:
        docx_bytes = generate_form_docx(area, interviewee, role, date)
        filename = f"formulario_{area}_{interviewee.replace(' ', '_') or 'entrevista'}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/vexia/transcricao")
def get_vexia_transcricao():
    """Retorna a transcrição da reunião com a Vexia."""
    import os
    path = os.path.join(os.path.dirname(__file__), "data", "vexia_transcricao.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"status": "ok", "text": f.read()}
    return {"status": "ok", "text": "Transcrição não disponível."}


@app.get("/api/vexia/resumo")
def get_vexia_resumo():
    """Retorna o resumo consolidado da análise Vexia."""
    import os
    path = os.path.join(os.path.dirname(__file__), "data", "vexia_resumo.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"status": "ok", "text": f.read()}
    return {"status": "ok", "text": "Resumo não disponível."}


@app.post("/api/forms/import")
async def import_form(file: UploadFile = File(...)):
    """Importa formulário .docx preenchido e extrai dados."""
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Apenas arquivos .docx são aceitos")
    content = await file.read()
    try:
        data = parse_form_docx(content)
        # Auto-save as interview
        if data["interviewee"]:
            transcript = data.get("transcript", "")
            interview = save_interview({
                "interviewer": data.get("interviewer", ""),
                "interviewee": data["interviewee"],
                "role": data.get("role", ""),
                "department": data.get("department", ""),
                "date": data.get("date", ""),
                "transcript": transcript,
                "ia_ready": bool(transcript and transcript.strip()),
            })
            data["interview_id"] = interview["id"]
            _maybe_auto_trigger_pipeline(data.get("department", ""), transcript)
        return {"status": "ok", "data": data}
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivo: {str(e)}")
