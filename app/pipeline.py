"""
Stoken Advisory — AI Analysis Pipeline
Orquestra a cadeia completa de 8 agentes para análise automática.

Pipeline:
1. PRISM → analisa cada entrevista (temas por pilar, sentimentos, insights)
2. ARIA → gera scores de maturidade por pilar (CMMI 1-5) com evidências
3. SENTINEL + NEXUS + CATALYST → riscos, benchmark, business cases (paralelo)
4. STRATEGOS + ATLAS → gap analysis e roadmap (paralelo)
5. SYNAPSE → consolidação holística de todos os 7 agentes
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
            max_tokens=agent.get("max_tokens", 4096),
            system=system,
            messages=[{"role": "user", "content": message}]
        )

        result = message_resp.content[0].text
        logger.info(f"Agent {agent_id}: {message_resp.usage.input_tokens}in/{message_resp.usage.output_tokens}out")
        return result

    except Exception as e:
        logger.error(f"Agent {agent_id} error: {e}")
        return None


def _load_vexia_context() -> str:
    """Loads Vexia BPO analysis summary for pipeline context."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    summary_path = os.path.join(data_dir, "vexia_resumo.txt")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


async def run_full_pipeline():
    """Executa o pipeline completo de análise com todos os 8 agentes."""
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

    # ─── Step 1: PRISM — Analyze each interview with pillar classification ──
    logger.info("Pipeline Step 1: PRISM — Interview Analysis")
    update_pipeline_status(step="PRISM: Analisando entrevistas")

    all_themes = []
    for interview in ia_interviews:
        prompt = f"""Analise esta entrevista do diagnóstico de supply chain da Santista S.A.

ENTREVISTADO: {interview['interviewee']}
CARGO: {interview['role']}
DEPARTAMENTO: {interview['department']}
PILAR PRINCIPAL: {interview['pillar'] or 'não definido'}
DATA: {interview['date']}

TRANSCRIÇÃO:
{interview['transcript']}

Extraia e retorne EXATAMENTE este JSON (sem markdown, sem explicação):
{{
  "themes": [
    {{
      "title": "<tema identificado>",
      "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
      "relevance": <1-5>,
      "evidence": "<citação ou referência da transcrição que sustenta>",
      "type": "problema|oportunidade|risco|força"
    }}
  ],
  "sentiment": "positivo|neutro|negativo|frustrado|urgente",
  "sentiment_detail": "<1 frase explicando o sentimento geral do entrevistado>",
  "contradictions": ["<contradição 1 com outras áreas>"],
  "quotes": ["<quote-chave 1>", "<quote-chave 2>", "<quote-chave 3>"],
  "gaps": [
    {{
      "area": "<área do gap>",
      "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
      "current_state": "<como está hoje>",
      "best_practice": "<como deveria ser>"
    }}
  ],
  "coverage": {{
    "processos": <0-5 relevância das informações para este pilar>,
    "sistemas": <0-5>,
    "operacoes": <0-5>,
    "organizacao": <0-5>,
    "roadmap": <0-5>
  }}
}}

IMPORTANTE:
- Classifique CADA tema por pilar — isso alimenta o diagnóstico de maturidade
- O campo "coverage" indica quanta informação útil esta entrevista trouxe para cada pilar
- Extraia no mínimo 5 e no máximo 10 temas
- Seja específico nas evidências — cite trechos reais da transcrição"""

        result = await _call_agent("prism", prompt)
        if result:
            update_interview_analysis(interview["id"], result)
            all_themes.append(f"[{interview['interviewee']} — {interview['role']} — {interview['department']}]:\n{result}")

    update_pipeline_status(step="PRISM: Concluído")

    # ─── Step 2: ARIA — Diagnostic scoring with evidence ────────────────────
    logger.info("Pipeline Step 2: ARIA — Diagnostic Scoring")
    update_pipeline_status(step="ARIA: Gerando scores por pilar")

    interview_context = "\n\n---\n\n".join(all_themes)
    diag_prompt = f"""Com base nas {len(ia_interviews)} entrevistas analisadas pelo PRISM abaixo, gere o diagnóstico de maturidade CMMI da Santista S.A.

ANÁLISES DO PRISM (temas já classificados por pilar):
{interview_context}

Retorne EXATAMENTE este JSON (sem markdown, sem explicação, apenas o JSON):
{{
  "geral": <float 1.0-5.0>,
  "processos": <float>,
  "sistemas": <float>,
  "operacoes": <float>,
  "organizacao": <float>,
  "roadmap": <float>,
  "resumo": "<parágrafo de 2-3 frases com diagnóstico executivo>",
  "evidencias": {{
    "processos": "<principal evidência das entrevistas que justifica o score>",
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
}}

REGRAS:
- "confianca" reflete a quantidade e qualidade de dados das entrevistas para aquele pilar
- Se poucas entrevistas cobrem um pilar, a confiança deve ser "baixa"
- Justifique cada score com evidência concreta das entrevistas
- Use o campo "coverage" do PRISM para calibrar a confiança"""

    diag_result = await _call_agent("aria", diag_prompt)
    if diag_result:
        try:
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

    # ─── Step 3: SENTINEL + NEXUS + CATALYST (parallel) ────────────────────
    logger.info("Pipeline Step 3: SENTINEL + NEXUS + CATALYST (parallel)")
    update_pipeline_status(step="Executando SENTINEL, NEXUS, CATALYST em paralelo")

    vexia_context = _load_vexia_context()
    context_for_agents = f"Dados das entrevistas:\n{interview_context}\n\nScores ARIA:\n{diag_result or 'não disponível'}"
    if vexia_context:
        context_for_agents += f"\n\nDIAGNÓSTICO BPO VEXIA (consultoria que opera Fiscal, Financeiro, RH/Folha, Contabilidade, Suprimentos, Compliance e TI da Santista):\n{vexia_context}"

    sentinel_task = _call_agent("sentinel",
        "Com base nos dados do diagnóstico e das entrevistas, identifique os TOP 5 riscos da Santista S.A. "
        "Para cada risco: título, categoria, probabilidade (1-5), impacto (1-5), "
        "valor financeiro estimado em R$, causa raiz, plano de mitigação com owner e prazo. "
        "Identifique riscos correlacionados (efeito cascata). Formato JSON array.",
        context_for_agents)

    nexus_task = _call_agent("nexus",
        "Compare a Santista S.A. com o benchmark do setor têxtil brasileiro (ABIT/IEMI). "
        "Para cada pilar (processos, sistemas, operações, organização, roadmap): "
        "score Santista, média setor, top quartil, gap em pontos e %. "
        "Identifique 5 best practices que a Santista deveria adotar com ROI estimado. "
        "Diferencie table stakes vs differentiators. Formato JSON.",
        context_for_agents)

    catalyst_task = _call_agent("catalyst",
        "Para as TOP 5 iniciativas de melhoria identificadas no diagnóstico, crie business case detalhado. "
        "Para cada: investimento inicial, custos recorrentes, benefício anual, payback, NPV 5 anos (WACC 14%), IRR. "
        "Apresente 3 cenários (pessimista -30%, base, otimista +30%). "
        "Inclua custos ocultos (change management, treinamento). Formato JSON array ordenado por NPV.",
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

    # ─── Step 4: STRATEGOS + ATLAS (parallel) ──────────────────────────────
    logger.info("Pipeline Step 4: STRATEGOS + ATLAS (parallel)")
    update_pipeline_status(step="Executando STRATEGOS e ATLAS em paralelo")

    context_step4 = (
        f"Dados das entrevistas (PRISM):\n{interview_context}\n\n"
        f"Scores ARIA:\n{diag_result or 'N/A'}\n\n"
        f"Riscos SENTINEL:\n{sentinel_result or 'N/A'}\n\n"
        f"Benchmark NEXUS:\n{nexus_result or 'N/A'}\n\n"
        f"Business Cases CATALYST:\n{catalyst_result or 'N/A'}"
    )
    if vexia_context:
        context_step4 += f"\n\nDIAGNÓSTICO BPO VEXIA:\n{vexia_context}"

    strategos_task = _call_agent("strategos",
        "Com base em todos os dados do diagnóstico (scores ARIA, riscos SENTINEL, benchmark NEXUS, "
        "temas do PRISM), mapeie os gaps estratégicos da Santista S.A.\n\n"
        "Para cada gap:\n"
        "- Pilar afetado\n"
        "- Estado atual (com evidência das entrevistas)\n"
        "- Estado alvo (target 3.5/5.0)\n"
        "- Impacto financeiro estimado em R$\n"
        "- Urgência (1-3): 1=imediato, 2=curto prazo, 3=médio prazo\n"
        "- Owner sugerido\n"
        "- Dependências com outros gaps\n"
        "- Quick fix (<30 dias) vs solução estrutural\n\n"
        "Estruture em árvore MECE. Formato markdown estruturado.",
        context_step4)

    atlas_task = _call_agent("atlas",
        "Com base nos gaps identificados, business cases e scores de maturidade, "
        "gere o roadmap de transformação da Santista S.A.\n\n"
        "Organize em 3 ondas:\n"
        "- Onda 1 — Quick Wins (0-3 meses): iniciativas de alto impacto e baixo esforço\n"
        "- Onda 2 — Estruturante (3-12 meses): fundações sistêmicas e processuais\n"
        "- Onda 3 — Transformacional (12-18+ meses): mudança cultural e digital\n\n"
        "Para cada iniciativa: scope, owner, budget, timeline, dependências, KPIs de sucesso, risco.\n"
        "Inclua OKRs trimestrais e plano de change management.\n"
        "Sinalize dependências críticas entre ondas. Formato markdown estruturado.",
        context_step4)

    strategos_result, atlas_result = await asyncio.gather(
        strategos_task, atlas_task
    )

    if strategos_result:
        set_analysis_result("gaps", strategos_result)
        update_pipeline_status(step="STRATEGOS: Concluído")
    if atlas_result:
        set_analysis_result("roadmap_atlas", atlas_result)
        update_pipeline_status(step="ATLAS: Concluído")

    # ─── Step 5: SYNAPSE — Holistic consolidation ──────────────────────────
    logger.info("Pipeline Step 5: SYNAPSE — Holistic Consolidation")
    update_pipeline_status(step="SYNAPSE: Consolidando análise holística")

    all_outputs = (
        f"DIAGNÓSTICO ARIA (scores e evidências):\n{diag_result or 'N/A'}\n\n"
        f"RISCOS SENTINEL:\n{sentinel_result or 'N/A'}\n\n"
        f"BENCHMARK NEXUS:\n{nexus_result or 'N/A'}\n\n"
        f"BUSINESS CASES CATALYST:\n{catalyst_result or 'N/A'}\n\n"
        f"GAPS STRATEGOS:\n{strategos_result or 'N/A'}\n\n"
        f"ROADMAP ATLAS:\n{atlas_result or 'N/A'}"
    )
    if vexia_context:
        all_outputs += f"\n\nDIAGNÓSTICO BPO VEXIA:\n{vexia_context}"

    synapse_result = await _call_agent("synapse",
        "Consolide TODOS os outputs dos 7 agentes especialistas num relatório executivo integrado.\n\n"
        "O relatório deve conter:\n"
        "1. Executive Summary (máx 5 parágrafos) — situação geral da Santista\n"
        "2. Mapa de Interdependências — onde problemas de um pilar impactam outros\n"
        "3. Análise de Coerência — o roadmap proposto endereça os gaps mais críticos?\n"
        "4. Temas Transversais — padrões que aparecem em múltiplos pilares/entrevistas\n"
        "5. Matriz de Valor Estratégico — urgência × impacto × viabilidade para cada iniciativa\n"
        "6. Top 5 Recomendações priorizadas para a diretoria\n"
        "7. Riscos de Execução que podem comprometer o plano\n\n"
        "Tom: consultor sênior apresentando para board de diretores.\n"
        "Formato: markdown estruturado com tabelas.",
        all_outputs)

    if synapse_result:
        set_analysis_result("synapse", synapse_result)
        update_pipeline_status(step="SYNAPSE: Concluído")

    # ─── Step 6: Generate consolidated insights ────────────────────────────
    logger.info("Pipeline Step 6: Generating consolidated insights")
    update_pipeline_status(step="Gerando insights consolidados")

    all_analysis = f"""DIAGNÓSTICO ARIA:
{diag_result or 'N/A'}

RISCOS SENTINEL:
{sentinel_result or 'N/A'}

BENCHMARK NEXUS:
{nexus_result or 'N/A'}

BUSINESS CASES CATALYST:
{catalyst_result or 'N/A'}

GAPS STRATEGOS:
{strategos_result or 'N/A'}

ROADMAP ATLAS:
{atlas_result or 'N/A'}

CONSOLIDAÇÃO SYNAPSE:
{synapse_result or 'N/A'}"""

    insights_prompt = f"""Com base em TODA a análise dos 8 agentes abaixo, gere 8 insights para o feed da plataforma Stoken Advisory.

{all_analysis}

Para cada insight, retorne EXATAMENTE este JSON array (sem markdown):
[
  {{
    "category": "risco|oportunidade|quickwin|estrategico",
    "impact": "alto|medio|baixo",
    "pillar": "processos|sistemas|operacoes|organizacao|roadmap",
    "title": "<título editorial, máx 100 chars>",
    "body": "<corpo de 2-3 frases descrevendo o insight com evidência concreta>",
    "estimated_value": "<ex: -R$ 850k/ano ou +R$ 420k/ano>",
    "value_type": "positive|negative",
    "origin": "<ex: Entrevista — Dir. TI + SENTINEL>",
    "benchmark": "<referência de benchmark relevante do NEXUS>",
    "suggested_action": "<ação concreta sugerida pelo ATLAS/STRATEGOS>",
    "validated": true
  }}
]

Gere exatamente 8 insights: 2 riscos, 2 oportunidades, 2 quick wins, 2 estratégicos.
Ordene por impacto (alto primeiro). Use dados reais das entrevistas e cruze com os achados dos agentes.
Os insights devem refletir a visão integrada do SYNAPSE, não apenas dados isolados."""

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
    logger.info("Pipeline complete! All 8 agents executed.")
