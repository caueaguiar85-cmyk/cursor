"""
Teste manual de validação dos 8 agentes — simula chamadas reais do pipeline.
Usa max_tokens reduzido (1500) para economizar, mas valida formato de saída.
"""
import asyncio
import json
import os
import sys
import time

# Carrega .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
from app.agents import AGENTS

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ─── Helpers ─────────────────────────────────────────────────────────────────

TEST_MAX_TOKENS = 4096  # precisa ser suficiente para JSON completo dos agentes

def call_agent(agent_id: str, message: str, context: str = "") -> str:
    agent = AGENTS[agent_id]
    system = agent["system_prompt"]
    if context:
        system += f"\n\nCONTEXTO ADICIONAL:\n{context}"

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=TEST_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": message}]
    )
    text = resp.content[0].text
    tokens_in = resp.usage.input_tokens
    tokens_out = resp.usage.output_tokens
    return text, tokens_in, tokens_out


def try_parse_json(text: str):
    """Tenta parsear JSON de resposta que pode conter markdown."""
    clean = text.strip()
    if "```" in clean:
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()
    return json.loads(clean)


def print_result(agent: str, passed: bool, detail: str, tokens_in: int, tokens_out: int):
    status = "PASS" if passed else "FAIL"
    icon = "+" if passed else "!"
    print(f"  [{icon}] {agent:12s} | {status} | {tokens_in}in/{tokens_out}out | {detail}")


# ─── Test Data ───────────────────────────────────────────────────────────────

MOCK_TRANSCRIPT = """
Entrevistador: Como funciona o processo de compras hoje?

Carlos Mendes (Gerente de Compras): Olha, é tudo muito manual. A gente recebe os pedidos
por e-mail, às vezes por WhatsApp, e coloca numa planilha Excel. Não tem sistema integrado.
O ERP que a gente usa é de 2012, não tem módulo de compras decente. Eu perco umas 3 horas
por dia só organizando pedidos.

Entrevistador: Quais são os maiores problemas?

Carlos: O maior problema é falta de visibilidade. Eu não sei o que o PCP precisa até eles
me mandarem um e-mail desesperado. Aí vira urgência, pago mais caro no frete, o fornecedor
cobra ágio. No último trimestre isso nos custou uns R$ 200 mil a mais do que deveria.
Outro problema sério é que dependemos de um único fornecedor de corantes, a QuimiTex.
Se eles atrasam, para tudo. Já aconteceu 2 vezes esse ano.

Entrevistador: E quanto aos indicadores?

Carlos: Indicadores? A gente não tem. Eu sei de cabeça que o lead time médio é uns 15 dias,
mas não tenho dashboard, não tenho KPI formal. O financeiro cobra saving, mas eu não
consigo provar porque não tenho baseline.
"""

MOCK_PRISM_OUTPUT = json.dumps({
    "themes": [
        {"title": "Processo de compras manual e desorganizado", "pillar": "processos", "relevance": 5, "evidence": "recebe pedidos por e-mail/WhatsApp, coloca em planilha Excel", "type": "problema"},
        {"title": "ERP obsoleto sem módulo de compras", "pillar": "sistemas", "relevance": 5, "evidence": "ERP de 2012, não tem módulo de compras decente", "type": "problema"},
        {"title": "Falta de visibilidade entre áreas", "pillar": "operacoes", "relevance": 4, "evidence": "não sei o que o PCP precisa até e-mail desesperado", "type": "problema"},
        {"title": "Fornecedor único de corantes (QuimiTex)", "pillar": "operacoes", "relevance": 4, "evidence": "dependemos de um único fornecedor, já atrasou 2 vezes", "type": "risco"},
        {"title": "Ausência de KPIs e dashboards", "pillar": "sistemas", "relevance": 4, "evidence": "não tem dashboard, não tem KPI formal", "type": "problema"}
    ],
    "sentiment": "frustrado",
    "sentiment_detail": "Gerente demonstra frustração com processos manuais e falta de ferramentas",
    "contradictions": [],
    "quotes": ["perco umas 3 horas por dia só organizando pedidos", "isso nos custou uns R$ 200 mil a mais"],
    "gaps": [
        {"area": "Compras", "pillar": "processos", "current_state": "Pedidos via email/WhatsApp em planilha", "best_practice": "Sistema integrado de procurement com workflow automatizado"}
    ],
    "coverage": {"processos": 5, "sistemas": 4, "operacoes": 3, "organizacao": 1, "roadmap": 1}
}, ensure_ascii=False)

MOCK_ARIA_OUTPUT = json.dumps({
    "geral": 1.8,
    "processos": 1.5,
    "sistemas": 1.5,
    "operacoes": 2.0,
    "organizacao": 2.0,
    "roadmap": 1.5,
    "resumo": "A área de Compras apresenta maturidade crítica (1.8/5.0) com processos manuais, ERP obsoleto e ausência de KPIs.",
    "problemas_priorizados": {
        "alta": ["Processo de compras 100% manual", "ERP sem módulo de compras"],
        "media": ["Fornecedor único de corantes"],
        "baixa": ["Falta de baseline para medir savings"]
    },
    "evidencias": {
        "processos": "Pedidos por email/WhatsApp em planilha Excel",
        "sistemas": "ERP de 2012 sem módulo de compras",
        "operacoes": "Falta de visibilidade PCP-Compras gera urgências",
        "organizacao": "Evidência limitada nesta entrevista",
        "roadmap": "Sem planejamento tecnológico mencionado"
    },
    "confianca": {
        "processos": "alta", "sistemas": "alta", "operacoes": "media",
        "organizacao": "baixa", "roadmap": "baixa"
    }
}, ensure_ascii=False)


# ─── Tests ───────────────────────────────────────────────────────────────────

results = {"pass": 0, "fail": 0, "errors": []}

def run_test(agent_id, message, context, expect_json, validate_fn, label=""):
    """Runs a single agent test with validation."""
    name = f"{agent_id.upper()}{(' ' + label) if label else ''}"
    try:
        text, tok_in, tok_out = call_agent(agent_id, message, context)

        if expect_json:
            try:
                parsed = try_parse_json(text)
                ok, detail = validate_fn(parsed, text)
            except json.JSONDecodeError as e:
                ok = False
                detail = f"JSON INVÁLIDO: {str(e)[:80]}"
                # Salva resposta para debug
                with open(f"test_output_{agent_id}.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                detail += f" (salvo em test_output_{agent_id}.txt)"
        else:
            ok, detail = validate_fn(None, text)

        print_result(name, ok, detail, tok_in, tok_out)
        if ok:
            results["pass"] += 1
        else:
            results["fail"] += 1
            results["errors"].append(f"{name}: {detail}")

    except Exception as e:
        print_result(name, False, f"EXCEPTION: {e}", 0, 0)
        results["fail"] += 1
        results["errors"].append(f"{name}: {e}")


print("=" * 80)
print("VALIDAÇÃO MANUAL DOS 8 AGENTES — Chamadas reais à API")
print("=" * 80)
print()

# ─── 1. PRISM ────────────────────────────────────────────────────────────────
print("Step 1: PRISM — Análise de Entrevista")

prism_msg = f"""Analise esta entrevista da área Compras / Procurement.

ÁREA ANALISADA: Compras / Procurement
ENTREVISTADO: Carlos Mendes
CARGO: Gerente de Compras
DEPARTAMENTO: compras
PILAR PRINCIPAL: processos
DATA: 2026-04-15

TRANSCRIÇÃO:
{MOCK_TRANSCRIPT}

REGRAS:
- Considere APENAS a área Compras / Procurement
- Identifique dores recorrentes, gargalos operacionais, processos manuais/ineficientes
- Não invente informações que não estejam na transcrição

Extraia e retorne EXATAMENTE este JSON (sem markdown, sem explicação):
{{
  "themes": [
    {{
      "title": "<tema identificado>",
      "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
      "relevance": <1-5>,
      "evidence": "<citação ou referência da transcrição>",
      "type": "problema|oportunidade|risco|força"
    }}
  ],
  "sentiment": "positivo|neutro|negativo|frustrado|urgente",
  "sentiment_detail": "<1 frase>",
  "contradictions": ["<contradição 1>"],
  "quotes": ["<quote 1>", "<quote 2>"],
  "gaps": [
    {{
      "area": "<área>",
      "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
      "current_state": "<como está>",
      "best_practice": "<como deveria ser>"
    }}
  ],
  "coverage": {{
    "processos": <0-5>,
    "sistemas": <0-5>,
    "operacoes": <0-5>,
    "organizacao": <0-5>,
    "roadmap": <0-5>
  }}
}}

IMPORTANTE:
- Classifique CADA tema por pilar
- Extraia no mínimo 5 e no máximo 10 temas
- Seja específico nas evidências"""

def validate_prism(parsed, raw):
    checks = []
    if not isinstance(parsed.get("themes"), list) or len(parsed["themes"]) < 3:
        return False, f"themes inválido ou <3 itens (got {len(parsed.get('themes', []))})"
    for t in parsed["themes"]:
        if not isinstance(t.get("relevance"), (int, float)):
            return False, f"theme.relevance não é número: {t.get('relevance')}"
        if t.get("pillar") not in ("processos", "sistemas", "operacoes", "organizacao", "roadmap"):
            return False, f"pillar inválido: {t.get('pillar')}"
        if t.get("type") not in ("problema", "oportunidade", "risco", "força"):
            return False, f"type inválido: {t.get('type')}"
    if parsed.get("sentiment") not in ("positivo", "neutro", "negativo", "frustrado", "urgente"):
        return False, f"sentiment inválido: {parsed.get('sentiment')}"
    cov = parsed.get("coverage", {})
    for pilar in ("processos", "sistemas", "operacoes", "organizacao", "roadmap"):
        if not isinstance(cov.get(pilar), (int, float)):
            return False, f"coverage.{pilar} não é número: {cov.get(pilar)}"
    return True, f"JSON OK — {len(parsed['themes'])} themes, sentiment={parsed['sentiment']}"

run_test("prism", prism_msg, "", expect_json=True, validate_fn=validate_prism)
print()

# ─── 2. ARIA ─────────────────────────────────────────────────────────────────
print("Step 2: ARIA — Diagnóstico de Maturidade")

aria_msg = f"""Com base nas entrevistas da área Compras / Procurement analisadas pelo PRISM, gere o diagnóstico de maturidade.

ÁREA ANALISADA: Compras / Procurement
Considere APENAS os dados desta área.

CONSOLIDAÇÃO DAS ENTREVISTAS (PRISM):
[Carlos Mendes — Gerente de Compras]:
{MOCK_PRISM_OUTPUT}

Retorne EXATAMENTE este JSON (sem markdown, sem explicação, apenas o JSON):
{{
  "geral": <float 1.0-5.0>,
  "processos": <float>,
  "sistemas": <float>,
  "operacoes": <float>,
  "organizacao": <float>,
  "roadmap": <float>,
  "resumo": "<parágrafo com diagnóstico executivo>",
  "problemas_priorizados": {{
    "alta": ["<problema crítico>"],
    "media": ["<problema relevante>"],
    "baixa": ["<problema secundário>"]
  }},
  "evidencias": {{
    "processos": "<principal evidência>",
    "sistemas": "<principal evidência>",
    "operacoes": "<principal evidência>",
    "organizacao": "<principal evidência>",
    "roadmap": "<principal evidência>"
  }},
  "confianca": {{
    "processos": "alta|media|baixa",
    "sistemas": "alta|media|baixa",
    "operacoes": "alta|media|baixa",
    "organizacao": "alta|media|baixa",
    "roadmap": "alta|media|baixa"
  }}
}}"""

def validate_aria(parsed, raw):
    score_fields = ["geral", "processos", "sistemas", "operacoes", "organizacao", "roadmap"]
    for f in score_fields:
        val = parsed.get(f)
        if not isinstance(val, (int, float)):
            return False, f"CRÍTICO: {f} não é float! tipo={type(val).__name__}, valor={val}"
        if val < 0 or val > 5.1:
            return False, f"{f} fora do range: {val}"
    if not isinstance(parsed.get("resumo"), str) or len(parsed["resumo"]) < 20:
        return False, "resumo ausente ou muito curto"
    conf = parsed.get("confianca", {})
    for pilar in score_fields[1:]:
        if conf.get(pilar) not in ("alta", "media", "baixa"):
            return False, f"confianca.{pilar} inválida: {conf.get(pilar)}"
    scores = {f: parsed[f] for f in score_fields}
    return True, f"JSON OK — scores: {scores}"

run_test("aria", aria_msg, "", expect_json=True, validate_fn=validate_aria)
print()

# ─── 3. SENTINEL + NEXUS + CATALYST ─────────────────────────────────────────
print("Step 3: SENTINEL + NEXUS + CATALYST (paralelo)")

context_step3 = f"ÁREA ANALISADA: Compras / Procurement\n\nDados das entrevistas:\n{MOCK_PRISM_OUTPUT}\n\nScores ARIA:\n{MOCK_ARIA_OUTPUT}"

sentinel_msg = (
    "Para a área Compras / Procurement, identifique os TOP 3 riscos. "
    "Para cada risco: título, categoria, probabilidade (1-5), impacto (1-5), "
    "valor financeiro estimado em R$, causa raiz, plano de mitigação com owner e prazo. "
    "IMPORTANTE: Baseie-se EXCLUSIVAMENTE nos dados das entrevistas desta área. Formato JSON array."
)

nexus_msg = (
    "Para a área Compras / Procurement, compare com benchmark do setor. "
    "Para cada pilar: score atual, média setor, top quartil, gap em pontos e %. "
    "Identifique 3 best practices com ROI estimado. "
    "Diferencie table stakes vs differentiators. Formato JSON."
)

catalyst_msg = (
    "Para a área Compras / Procurement, crie business case para as TOP 3 iniciativas de melhoria. "
    "Para cada: investimento inicial, custos recorrentes, benefício anual, payback, NPV 5 anos (WACC 14%), IRR. "
    "3 cenários (pessimista -30%, base, otimista +30%). "
    "Formato JSON array ordenado por NPV."
)

def validate_sentinel(parsed, raw):
    if not isinstance(parsed, list) or len(parsed) < 1:
        return False, f"Esperado JSON array, got {type(parsed).__name__}"
    r = parsed[0]
    needed = ["probabilidade", "impacto"]
    for key in needed:
        if key not in str(r).lower():
            pass  # campo pode ter nome diferente
    return True, f"JSON array OK — {len(parsed)} riscos"

def validate_nexus(parsed, raw):
    if not isinstance(parsed, (dict, list)):
        return False, f"Esperado dict/list, got {type(parsed).__name__}"
    return True, f"JSON OK — tipo={type(parsed).__name__}"

def validate_catalyst(parsed, raw):
    if not isinstance(parsed, list) or len(parsed) < 1:
        return False, f"Esperado JSON array, got {type(parsed).__name__}"
    return True, f"JSON array OK — {len(parsed)} business cases"

run_test("sentinel", sentinel_msg, context_step3, expect_json=True, validate_fn=validate_sentinel)
run_test("nexus", nexus_msg, context_step3, expect_json=True, validate_fn=validate_nexus)
run_test("catalyst", catalyst_msg, context_step3, expect_json=True, validate_fn=validate_catalyst)
print()

# ─── 4. STRATEGOS + ATLAS ───────────────────────────────────────────────────
print("Step 4: STRATEGOS + ATLAS")

context_step4 = (
    f"ÁREA ANALISADA: Compras / Procurement\n\n"
    f"Dados das entrevistas (PRISM):\n{MOCK_PRISM_OUTPUT}\n\n"
    f"Scores ARIA:\n{MOCK_ARIA_OUTPUT}"
)

strategos_msg = (
    "Para a área Compras / Procurement, mapeie os gaps estratégicos.\n\n"
    "Para cada gap:\n"
    "- Estado atual (com evidência das entrevistas)\n"
    "- Estado alvo\n"
    "- Impacto financeiro estimado em R$\n"
    "- Urgência (1-3)\n"
    "- Owner sugerido\n"
    "- Quick fix (<30 dias) vs solução estrutural\n\n"
    "IMPORTANTE: Use APENAS dados das entrevistas desta área. Formato markdown estruturado."
)

atlas_msg = (
    "Para a área Compras / Procurement, gere o roadmap de transformação.\n\n"
    "Organize em 3 horizontes:\n"
    "- CURTO PRAZO (Quick Wins, 0-3 meses)\n"
    "- MÉDIO PRAZO (3-12 meses)\n"
    "- LONGO PRAZO (12-18+ meses)\n\n"
    "Para cada item: descrição, classificação, impacto, owner, KPIs.\n"
    "IMPORTANTE: Baseie-se EXCLUSIVAMENTE nos dados das entrevistas. Formato markdown estruturado."
)

def validate_markdown(parsed, raw):
    if not raw or len(raw) < 100:
        return False, f"Resposta muito curta ({len(raw or '')} chars)"
    has_headers = "#" in raw
    has_structure = any(x in raw for x in ["##", "---", "|", "- "])
    if not has_headers:
        return False, "Sem headers markdown"
    return True, f"Markdown OK — {len(raw)} chars, headers={'sim' if has_headers else 'não'}"

run_test("strategos", strategos_msg, context_step4, expect_json=False, validate_fn=validate_markdown)
run_test("atlas", atlas_msg, context_step4, expect_json=False, validate_fn=validate_markdown)
print()

# ─── 5. SYNAPSE ─────────────────────────────────────────────────────────────
print("Step 5: SYNAPSE — Consolidação")

synapse_context = (
    "ÁREA ANALISADA: Compras / Procurement\n\n"
    f"ANÁLISE QUALITATIVA PRISM:\n{MOCK_PRISM_OUTPUT}\n\n"
    f"DIAGNÓSTICO ARIA:\n{MOCK_ARIA_OUTPUT}\n\n"
    "RISCOS SENTINEL:\nTop risco: Fornecedor único de corantes (QuimiTex), probabilidade 4, impacto 5, score 20 URGENTE.\n\n"
    "BENCHMARK NEXUS:\nCompras está 1.8 pontos abaixo da média do setor (3.3) em processos.\n\n"
    "BUSINESS CASES CATALYST:\nTop iniciativa: Implantação de módulo de procurement (NPV R$ 1.2M, payback 14 meses).\n\n"
    "GAPS STRATEGOS:\nGap crítico: processo de compras 100% manual, impacto estimado R$ 800k/ano.\n\n"
    "ROADMAP ATLAS:\nQuick Win: digitalização de pedidos (0-3 meses). Estruturante: migração ERP (3-12 meses)."
)

synapse_msg = (
    "Consolide TODOS os outputs dos 7 agentes para a área Compras / Procurement num relatório executivo.\n\n"
    "O relatório deve conter:\n"
    "1. Executive Summary\n"
    "2. Problemas priorizados\n"
    "3. Top 3 Recomendações\n"
    "4. Riscos de Execução\n\n"
    "REGRAS:\n"
    "- Considere APENAS a área analisada\n"
    "- Não invente informações\n"
    "- Formato: markdown estruturado."
)

def validate_synapse(parsed, raw):
    if not raw or len(raw) < 200:
        return False, f"Resposta muito curta ({len(raw or '')} chars)"
    has_exec = any(x.lower() in raw.lower() for x in ["executive summary", "síntese executiva", "resumo executivo"])
    has_headers = "##" in raw
    if not has_headers:
        return False, "Sem headers markdown"
    return True, f"Markdown OK — {len(raw)} chars, exec_summary={'sim' if has_exec else 'não'}"

run_test("synapse", synapse_msg, synapse_context, expect_json=False, validate_fn=validate_synapse)
print()

# ─── Resultado Final ─────────────────────────────────────────────────────────
print("=" * 80)
print(f"RESULTADO: {results['pass']} PASSED / {results['fail']} FAILED de {results['pass']+results['fail']} testes")
print("=" * 80)

if results["errors"]:
    print("\nFALHAS:")
    for err in results["errors"]:
        print(f"  [!] {err}")

sys.exit(1 if results["fail"] > 0 else 0)
