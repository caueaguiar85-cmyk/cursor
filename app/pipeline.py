"""
Stoken Advisory — AI Analysis Pipeline
Orquestra a cadeia de agentes para análise automática.

Pipeline:
1. PRISM → analisa cada entrevista (temas, sentimentos, insights)
2. ARIA → gera scores de maturidade por pilar (CMMI 1-5)
3. SENTINEL → identifica riscos com matriz probabilidade×impacto
4. NEXUS → benchmark vs setor têxtil
5. CATALYST → business case e ROI por iniciativa
6. Gera insights consolidados para o feed
"""

import asyncio
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


async def _call_agent(agent_id: str, message: str, context: str = "") -> Optional[str]:
    """Chama um agente via Claude API. Retorna texto ou None em caso de erro."""
    from app.agents import AGENTS

    agent = AGENTS.get(agent_id)
    if not agent:
        logger.error(f"Agent {agent_id} not found")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        system = agent["system_prompt"]
        if context:
            system += f"\n\nCONTEXTO ADICIONAL:\n{context}"

        message_resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": message}]
        )

        result = message_resp.content[0].text
        logger.info(f"Agent {agent_id}: {message_resp.usage.input_tokens}in/{message_resp.usage.output_tokens}out")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id} error: {e}")
        return None


async def run_full_pipeline():
    """Executa o pipeline completo de análise."""
    from app.datastore import (
        get_interviews, update_interview_analysis,
        set_diagnostic_scores, set_analysis_result,
        set_insights, update_pipeline_status
    )

    interviews = get_interviews()
    ia_interviews = [i for i in interviews if i.get("ia_ready") and i.get("transcript")]

    if not ia_interviews:
        logger.warning("No IA-ready interviews to analyze")
        update_pipeline_status(running=False, error="Nenhuma entrevista com transcrição marcada para IA")
        return

    update_pipeline_status(running=True)

    # ─── Step 1: PRISM — Analyze each interview ──────────────────────────
    logger.info("Pipeline Step 1: PRISM — Interview Analysis")
    update_pipeline_status(step="PRISM: Analisando entrevistas")

    all_themes = []
    for interview in ia_interviews:
        prompt = f"""Analise esta entrevista:

ENTREVISTADO: {interview['interviewee']}
CARGO: {interview['role']}
DEPARTAMENTO: {interview['department']}
PILAR: {interview['pillar']}
DATA: {interview['date']}

TRANSCRIÇÃO:
{interview['transcript']}

Extraia:
1. Top 5 temas/findings principais
2. Sentimento geral (positivo/neutro/negativo/frustrado)
3. Contradições com outras áreas (se percebermos)
4. 3 quotes-chave que ilustrem os findings
5. Gaps identificados vs best practice

Formate em JSON com keys: themes, sentiment, contradictions, quotes, gaps"""

        result = await _call_agent("prism", prompt)
        if result:
            update_interview_analysis(interview["id"], result)
            all_themes.append(f"[{interview['interviewee']} - {interview['role']}]: {result}")

    update_pipeline_status(step="PRISM: Concluído")

    # ─── Step 2: ARIA — Diagnostic scoring ────────────────────────────────
    logger.info("Pipeline Step 2: ARIA — Diagnostic Scoring")
    update_pipeline_status(step="ARIA: Gerando scores por pilar")

    interview_context = "\n\n---\n\n".join(all_themes)
    diag_prompt = f"""Com base nas {len(ia_interviews)} entrevistas analisadas abaixo, gere o diagnóstico de maturidade CMMI da Santista S.A.

ENTREVISTAS ANALISADAS:
{interview_context}

Retorne EXATAMENTE este JSON (sem markdown, sem explicação, apenas o JSON):
{{
  "geral": <float 1.0-5.0>,
  "processos": <float>,
  "sistemas": <float>,
  "operacoes": <float>,
  "organizacao": <float>,
  "roadmap": <float>,
  "resumo": "<parágrafo de 2-3 frases com diagnóstico executivo>"
}}"""

    diag_result = await _call_agent("aria", diag_prompt)
    if diag_result:
        try:
            # Try to extract JSON from response
            json_str = diag_result
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                json_str = json_str.strip()
            scores = json.loads(json_str)
            set_diagnostic_scores(scores)
            set_analysis_result("diagnostic", diag_result)
        except json.JSONDecodeError:
            logger.warning("Could not parse ARIA JSON, saving raw")
            set_analysis_result("diagnostic", diag_result)

    update_pipeline_status(step="ARIA: Concluído")

    # ─── Step 3: SENTINEL + NEXUS + CATALYST (parallel) ──────────────────
    logger.info("Pipeline Step 3: SENTINEL + NEXUS + CATALYST (parallel)")
    update_pipeline_status(step="Executando SENTINEL, NEXUS, CATALYST em paralelo")

    context_for_agents = f"Dados das entrevistas:\n{interview_context}\n\nScores ARIA:\n{diag_result or 'não disponível'}"

    sentinel_task = _call_agent("sentinel",
        "Com base nos dados do diagnóstico, identifique os TOP 5 riscos da Santista S.A. "
        "Para cada risco: título, categoria, probabilidade (1-5), impacto (1-5), "
        "valor financeiro estimado, e plano de mitigação. Formato JSON array.",
        context_for_agents)

    nexus_task = _call_agent("nexus",
        "Compare a Santista S.A. com o benchmark do setor têxtil brasileiro (ABIT). "
        "Para cada pilar, indique: score Santista, média setor, top quartil, gap. "
        "Identifique 3 best practices que a Santista deveria adotar. Formato JSON.",
        context_for_agents)

    catalyst_task = _call_agent("catalyst",
        "Para as TOP 5 iniciativas de melhoria identificadas, crie business case resumido. "
        "Para cada: investimento, benefício anual, payback, NPV 3 anos, risco. "
        "Formato JSON array ordenado por NPV.",
        context_for_agents)

    sentinel_result, nexus_result, catalyst_result = await asyncio.gather(
        sentinel_task, nexus_task, catalyst_task
    )

    if sentinel_result:
        set_analysis_result("risks", sentinel_result)
        update_pipeline_status(step="SENTINEL: Concluído")
    if nexus_result:
        set_analysis_result("benchmark", nexus_result)
        update_pipeline_status(step="NEXUS: Concluído")
    if catalyst_result:
        set_analysis_result("business_cases", catalyst_result)
        update_pipeline_status(step="CATALYST: Concluído")

    # ─── Step 4: Generate consolidated insights ──────────────────────────
    logger.info("Pipeline Step 4: Generating consolidated insights")
    update_pipeline_status(step="Gerando insights consolidados")

    all_analysis = f"""DIAGNÓSTICO ARIA:
{diag_result or 'N/A'}

RISCOS SENTINEL:
{sentinel_result or 'N/A'}

BENCHMARK NEXUS:
{nexus_result or 'N/A'}

BUSINESS CASES CATALYST:
{catalyst_result or 'N/A'}"""

    insights_prompt = f"""Com base em toda a análise abaixo, gere 8 insights para o feed da plataforma Stoken Advisory.

{all_analysis}

Para cada insight, retorne EXATAMENTE este JSON array (sem markdown):
[
  {{
    "category": "risco|oportunidade|quickwin|estrategico",
    "impact": "alto|medio|baixo",
    "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
    "title": "<título editorial, máx 100 chars>",
    "body": "<corpo de 2-3 frases descrevendo o insight>",
    "estimated_value": "<ex: -R$ 850k/ano ou +R$ 420k/ano>",
    "value_type": "positive|negative",
    "origin": "<ex: Entrevista — Dir. TI>",
    "benchmark": "<referência de benchmark relevante>",
    "suggested_action": "<ação concreta sugerida>",
    "validated": true
  }}
]

Gere exatamente 8 insights: 2 riscos, 2 oportunidades, 2 quick wins, 2 estratégicos.
Ordene por impacto (alto primeiro). Use dados reais das entrevistas."""

    insights_result = await _call_agent("aria", insights_prompt)
    if insights_result:
        try:
            json_str = insights_result
            if "```" in json_str:
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
                json_str = json_str.strip()
            insights_list = json.loads(json_str)
            if isinstance(insights_list, list):
                set_insights(insights_list)
                set_analysis_result("insights", insights_result)
        except json.JSONDecodeError:
            logger.warning("Could not parse insights JSON, saving raw")
            set_analysis_result("insights_raw", insights_result)

    update_pipeline_status(step="Insights: Concluído")
    update_pipeline_status(running=False)
    logger.info("Pipeline complete!")
