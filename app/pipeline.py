"""
Stoken Advisory — AI Analysis Pipeline
Orquestra a cadeia completa de 8 agentes para análise automática.

Pipeline por área:
1. Agrupa entrevistas por departamento/área
2. Para cada área, roda a cadeia de 8 agentes
3. Consolidação global com SYNAPSE + geração de insights
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

AREA_LABELS = {
    "supply-chain": "Supply Chain",
    "producao": "Produção / PCP",
    "comercial": "Comercial / Vendas",
    "logistica": "Logística",
    "ti": "Tecnologia / TI",
    "financeiro": "Financeiro / Controladoria",
    "qualidade": "Qualidade",
    "compras": "Compras / Procurement",
    "rh": "RH / Pessoas",
    "diretoria": "Diretoria Geral",
}


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
            model="claude-sonnet-4-6",
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


def _parse_json_result(text: str):
    """Tenta parsear JSON de uma resposta que pode conter markdown."""
    json_str = text
    if "```" in json_str:
        json_str = json_str.split("```")[1]
        if json_str.startswith("json"):
            json_str = json_str[4:]
        json_str = json_str.strip()
    return json.loads(json_str)


# ─── Pipeline por área individual ────────────────────────────────────────────

async def _run_area_pipeline(area: str, interviews: list) -> dict:
    """Roda a cadeia de 8 agentes para uma única área."""
    from app.datastore import (
        update_interview_analysis, update_pipeline_status,
        set_analysis_result_for_area,
    )

    area_label = AREA_LABELS.get(area, area.upper())
    vexia_context = _load_vexia_context()
    results = {}

    # ─── Step 1: PRISM — Analisa cada entrevista ─────────────────────────
    logger.info(f"[{area}] Step 1: PRISM — Interview Analysis")
    update_pipeline_status(step=f"PRISM [{area_label}]: Analisando {len(interviews)} entrevistas")

    all_themes = []
    for interview in interviews:
        prompt = f"""Analise esta entrevista da área {area_label}.

ÁREA ANALISADA: {area_label}
ENTREVISTADO: {interview['interviewee']}
CARGO: {interview['role']}
DEPARTAMENTO: {interview['department']}
PILAR PRINCIPAL: {interview['pillar'] or 'não definido'}
DATA: {interview['date']}

TRANSCRIÇÃO:
{interview['transcript']}

REGRAS:
- Considere APENAS a área {area_label} — não misture com outras áreas
- Identifique dores recorrentes, gargalos operacionais, processos manuais/ineficientes
- Identifique riscos: erro humano, retrabalho, falta de governança, baixa escalabilidade
- Não invente informações que não estejam na transcrição

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
- Extraia no mínimo 5 e no máximo 10 temas
- Seja específico nas evidências — cite trechos reais da transcrição"""

        result = await _call_agent("prism", prompt)
        if result:
            update_interview_analysis(interview["id"], result)
            all_themes.append(f"[{interview['interviewee']} — {interview['role']}]:\n{result}")

    interview_context = "\n\n---\n\n".join(all_themes)
    results["interview_context"] = interview_context

    # ─── Step 2: ARIA — Diagnóstico de maturidade da área ────────────────
    logger.info(f"[{area}] Step 2: ARIA — Diagnostic Scoring")
    update_pipeline_status(step=f"ARIA [{area_label}]: Gerando scores")

    diag_prompt = f"""Com base nas {len(interviews)} entrevistas da área {area_label} analisadas pelo PRISM, gere o diagnóstico de maturidade.

ÁREA ANALISADA: {area_label}
Considere APENAS os dados desta área. Não generalize.

CONSOLIDAÇÃO DAS ENTREVISTAS (PRISM):
{interview_context}

ETAPA 1 — Consolidação: Antes de pontuar, identifique:
- Dores recorrentes entre os entrevistados
- Gargalos operacionais
- Processos manuais ou ineficientes
- Divergências de percepção entre entrevistados

ETAPA 2 — Classificação de prioridade:
- Alta (críticos): impactam diretamente operação ou resultado
- Média (relevantes): afetam eficiência e qualidade
- Baixa (secundários): impacto limitado ou pontual

Retorne EXATAMENTE este JSON (sem markdown, sem explicação, apenas o JSON):
{{
  "geral": <float 1.0-5.0>,
  "processos": <float>,
  "sistemas": <float>,
  "operacoes": <float>,
  "organizacao": <float>,
  "roadmap": <float>,
  "resumo": "<parágrafo com diagnóstico executivo da área {area_label}>",
  "problemas_priorizados": {{
    "alta": ["<problema crítico 1>", "<problema crítico 2>"],
    "media": ["<problema relevante 1>"],
    "baixa": ["<problema secundário 1>"]
  }},
  "evidencias": {{
    "processos": "<principal evidência das entrevistas>",
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

    diag_result = await _call_agent("aria", diag_prompt)
    results["diag_result"] = diag_result
    if diag_result:
        set_analysis_result_for_area(area, "aria_analysis", diag_result)

    # ─── Step 3: SENTINEL + NEXUS + CATALYST (paralelo) ──────────────────
    logger.info(f"[{area}] Step 3: SENTINEL + NEXUS + CATALYST")
    update_pipeline_status(step=f"[{area_label}]: SENTINEL, NEXUS, CATALYST em paralelo")

    context_for_agents = f"ÁREA ANALISADA: {area_label}\n\nDados das entrevistas da área:\n{interview_context}\n\nScores ARIA:\n{diag_result or 'não disponível'}"
    if vexia_context:
        context_for_agents += f"\n\nDIAGNÓSTICO BPO VEXIA:\n{vexia_context}"

    sentinel_task = _call_agent("sentinel",
        f"Para a área {area_label}, com base nas entrevistas e diagnóstico, identifique os TOP 5 riscos. "
        "Para cada risco: título, categoria, probabilidade (1-5), impacto (1-5), "
        "valor financeiro estimado em R$, causa raiz, plano de mitigação com owner e prazo. "
        "Identifique riscos correlacionados (efeito cascata). "
        "IMPORTANTE: Baseie-se EXCLUSIVAMENTE nos dados das entrevistas desta área. Formato JSON array.",
        context_for_agents)

    nexus_task = _call_agent("nexus",
        f"Para a área {area_label}, compare com benchmark do setor. "
        "Para cada pilar: score atual, média setor, top quartil, gap em pontos e %. "
        "Identifique 5 best practices com ROI estimado. "
        "Diferencie table stakes vs differentiators. Formato JSON.",
        context_for_agents)

    catalyst_task = _call_agent("catalyst",
        f"Para a área {area_label}, crie business case para as TOP 5 iniciativas de melhoria. "
        "Para cada: investimento inicial, custos recorrentes, benefício anual, payback, NPV 5 anos (WACC 14%), IRR. "
        "3 cenários (pessimista -30%, base, otimista +30%). "
        "Classifique cada solução como: automação, integração de sistemas, uso de IA, ou melhoria de processo. "
        "Formato JSON array ordenado por NPV.",
        context_for_agents)

    sentinel_result, nexus_result, catalyst_result = await asyncio.gather(
        sentinel_task, nexus_task, catalyst_task
    )

    results["sentinel_result"] = sentinel_result
    results["nexus_result"] = nexus_result
    results["catalyst_result"] = catalyst_result

    if sentinel_result:
        set_analysis_result_for_area(area, "risks", sentinel_result)
    if nexus_result:
        set_analysis_result_for_area(area, "benchmark", nexus_result)
    if catalyst_result:
        set_analysis_result_for_area(area, "business_cases", catalyst_result)

    # ─── Step 4: STRATEGOS + ATLAS (paralelo) ────────────────────────────
    logger.info(f"[{area}] Step 4: STRATEGOS + ATLAS")
    update_pipeline_status(step=f"[{area_label}]: STRATEGOS e ATLAS em paralelo")

    context_step4 = (
        f"ÁREA ANALISADA: {area_label}\n\n"
        f"Dados das entrevistas (PRISM):\n{interview_context}\n\n"
        f"Scores ARIA:\n{diag_result or 'N/A'}\n\n"
        f"Riscos SENTINEL:\n{sentinel_result or 'N/A'}\n\n"
        f"Benchmark NEXUS:\n{nexus_result or 'N/A'}\n\n"
        f"Business Cases CATALYST:\n{catalyst_result or 'N/A'}"
    )
    if vexia_context:
        context_step4 += f"\n\nDIAGNÓSTICO BPO VEXIA:\n{vexia_context}"

    strategos_task = _call_agent("strategos",
        f"Para a área {area_label}, mapeie os gaps estratégicos.\n\n"
        "Para cada gap:\n"
        "- Estado atual (com evidência das entrevistas)\n"
        "- Estado alvo\n"
        "- Impacto financeiro estimado em R$\n"
        "- Urgência (1-3): 1=imediato, 2=curto prazo, 3=médio prazo\n"
        "- Owner sugerido\n"
        "- Dependências com outros gaps\n"
        "- Quick fix (<30 dias) vs solução estrutural\n\n"
        "Conecte problemas → causas → soluções. "
        "IMPORTANTE: Use APENAS dados das entrevistas desta área. "
        "Formato markdown estruturado.",
        context_step4)

    atlas_task = _call_agent("atlas",
        f"Para a área {area_label}, gere o roadmap de transformação.\n\n"
        "Organize em 3 horizontes:\n"
        "- CURTO PRAZO (Quick Wins, 0-3 meses): baixo esforço, alto impacto, implementação rápida\n"
        "- MÉDIO PRAZO (3-12 meses): estruturação de processos, automações, melhoria de fluxos\n"
        "- LONGO PRAZO (12-18+ meses): mudanças estruturais, soluções escaláveis, evolução de maturidade\n\n"
        "Para cada item:\n"
        "- Descrição clara da solução\n"
        "- Classificação: automação | integração de sistemas | uso de IA | melhoria de processo\n"
        "- Impacto esperado no negócio\n"
        "- Owner, budget, timeline, KPIs de sucesso\n\n"
        "IMPORTANTE: Baseie-se EXCLUSIVAMENTE nos dados das entrevistas desta área. "
        "Formato markdown estruturado.",
        context_step4)

    strategos_result, atlas_result = await asyncio.gather(
        strategos_task, atlas_task
    )

    results["strategos_result"] = strategos_result
    results["atlas_result"] = atlas_result

    if strategos_result:
        set_analysis_result_for_area(area, "gaps", strategos_result)
    if atlas_result:
        set_analysis_result_for_area(area, "roadmap_atlas", atlas_result)

    # ─── Step 5: SYNAPSE — Consolidação da área ──────────────────────────
    logger.info(f"[{area}] Step 5: SYNAPSE — Area Consolidation")
    update_pipeline_status(step=f"SYNAPSE [{area_label}]: Consolidando")

    all_outputs = (
        f"ÁREA ANALISADA: {area_label}\n\n"
        f"ANÁLISE QUALITATIVA PRISM:\n{interview_context or 'N/A'}\n\n"
        f"DIAGNÓSTICO ARIA:\n{diag_result or 'N/A'}\n\n"
        f"RISCOS SENTINEL:\n{sentinel_result or 'N/A'}\n\n"
        f"BENCHMARK NEXUS:\n{nexus_result or 'N/A'}\n\n"
        f"BUSINESS CASES CATALYST:\n{catalyst_result or 'N/A'}\n\n"
        f"GAPS STRATEGOS:\n{strategos_result or 'N/A'}\n\n"
        f"ROADMAP ATLAS:\n{atlas_result or 'N/A'}"
    )

    synapse_result = await _call_agent("synapse",
        f"Consolide TODOS os outputs dos 7 agentes para a área {area_label} num relatório executivo.\n\n"
        "O relatório deve conter:\n"
        "1. Executive Summary — situação da área\n"
        "2. Problemas priorizados (alta/média/baixa prioridade)\n"
        "3. Padrões e recorrências identificados entre entrevistados\n"
        "4. Divergências de percepção entre entrevistados\n"
        "5. Roadmap por horizonte (curto/médio/longo prazo)\n"
        "6. Top 5 Recomendações priorizadas\n"
        "7. Riscos de Execução\n\n"
        "REGRAS:\n"
        "- Considere APENAS a área analisada\n"
        "- Não invente informações que não estejam nas entrevistas\n"
        "- Conecte problemas → causas → soluções\n"
        "- Formato: markdown estruturado com tabelas.",
        all_outputs)

    results["synapse_result"] = synapse_result

    if synapse_result:
        set_analysis_result_for_area(area, "synapse", synapse_result)

    update_pipeline_status(step=f"[{area_label}]: Concluído")
    logger.info(f"[{area}] Area pipeline complete.")
    return results


# ─── Consolidação global ─────────────────────────────────────────────────────

async def _run_global_consolidation(area_results: dict):
    """Consolida resultados de todas as áreas num diagnóstico global."""
    from app.datastore import (
        set_analysis_result, update_pipeline_status,
    )

    update_pipeline_status(step="SYNAPSE GLOBAL: Consolidando todas as áreas")

    # Monta contexto com os resultados de SYNAPSE de cada área
    area_summaries = []
    for area, res in area_results.items():
        area_label = AREA_LABELS.get(area, area.upper())
        synapse = res.get("synapse_result", "N/A")
        diag = res.get("diag_result", "N/A")
        area_summaries.append(f"═══ ÁREA: {area_label} ═══\nDIAGNÓSTICO:\n{diag}\n\nCONSOLIDAÇÃO:\n{synapse}")

    global_context = "\n\n".join(area_summaries)

    # SYNAPSE global
    synapse_global = await _call_agent("synapse",
        f"Consolide os diagnósticos de {len(area_results)} áreas num relatório executivo global.\n\n"
        "O relatório deve conter:\n"
        "1. Executive Summary — visão geral da organização\n"
        "2. Mapa de Interdependências — onde problemas de uma área impactam outras\n"
        "3. Temas Transversais — padrões que aparecem em múltiplas áreas\n"
        "4. Matriz de Valor Estratégico — urgência × impacto × viabilidade\n"
        "5. Top 5 Recomendações priorizadas para a diretoria\n"
        "6. Riscos de Execução cross-área\n\n"
        "Tom: consultor sênior apresentando para board de diretores.\n"
        "Formato: markdown estruturado com tabelas.",
        global_context)

    if synapse_global:
        set_analysis_result("synapse", synapse_global)

    update_pipeline_status(step="Consolidação global: Concluída")


# ─── Entry points ────────────────────────────────────────────────────────────

async def run_full_pipeline():
    """Executa o pipeline completo: todas as áreas + consolidação global."""
    from app.datastore import (
        get_interviews, update_pipeline_status
    )

    try:
        update_pipeline_status(running=True)

        interviews = get_interviews()
        ia_interviews = [i for i in interviews if i.get("transcript")]

        if not ia_interviews:
            logger.warning("No IA-ready interviews to analyze")
            update_pipeline_status(running=False, error="Nenhuma entrevista com transcrição marcada para IA")
            return

        # Agrupa por área
        area_interviews = defaultdict(list)
        for iv in ia_interviews:
            dept = iv.get("department", "geral")
            area_interviews[dept].append(iv)

        logger.info(f"Pipeline: {len(ia_interviews)} entrevistas em {len(area_interviews)} áreas: {list(area_interviews.keys())}")

        # Processa cada área (pipeline + estratégia automática)
        area_results = {}
        for area, interviews in area_interviews.items():
            area_label = AREA_LABELS.get(area, area.upper())
            logger.info(f"Processing area: {area_label} ({len(interviews)} entrevistas)")
            update_pipeline_status(step=f"Processando área: {area_label}")
            area_results[area] = await _run_area_pipeline(area, interviews)

            # Auto-gera estratégia após pipeline da área
            logger.info(f"[{area}] Auto-generating strategy...")
            update_pipeline_status(step=f"Gerando estratégia para {area_label}...")
            await _run_strategy_steps(area)

        # Consolidação global
        if len(area_results) > 0:
            await _run_global_consolidation(area_results)

        update_pipeline_status(running=False)
        logger.info(f"Pipeline complete! {len(area_results)} áreas processadas.")

    except Exception as e:
        logger.error(f"Pipeline crashed: {e}")
        try:
            update_pipeline_status(running=False, error=f"Pipeline error: {str(e)[:200]}")
        except Exception:
            pass


async def run_area_pipeline(area: str):
    """Executa o pipeline para uma única área."""
    from app.datastore import get_interviews, update_pipeline_status

    try:
        update_pipeline_status(running=True)

        interviews = get_interviews()
        area_interviews = [i for i in interviews
                           if i.get("transcript")
                           and i.get("department") == area]

        if not area_interviews:
            area_label = AREA_LABELS.get(area, area)
            update_pipeline_status(running=False, error=f"Nenhuma entrevista para a área {area_label}")
            return

        await _run_area_pipeline(area, area_interviews)

        # Auto-gera estratégia após pipeline da área
        logger.info(f"[{area}] Auto-generating strategy after pipeline...")
        update_pipeline_status(step=f"Gerando estratégia para {area_label}...")
        await _run_strategy_steps(area)

        update_pipeline_status(running=False)

    except Exception as e:
        logger.error(f"Area pipeline crashed [{area}]: {e}")
        try:
            update_pipeline_status(running=False, error=f"Pipeline error [{area}]: {str(e)[:200]}")
        except Exception:
            pass


# ─── Pipeline de Estratégia por Área ─────────────────────────────────────────

async def _run_strategy_steps(area: str):
    """Executa os 3 steps de estratégia para uma área (sem controlar running status)."""
    from app.datastore import (
        get_interviews, update_pipeline_status,
        set_analysis_result_for_area, get_analysis_results_for_area,
    )

    area_label = AREA_LABELS.get(area, area.upper())

    # Carrega entrevistas da área
    interviews = get_interviews()
    area_interviews = [i for i in interviews
                       if i.get("transcript")
                       and i.get("department") == area]

    if not area_interviews:
        return

    # Consolida todas as entrevistas da área como contexto
    interview_parts = []
    for iv in area_interviews:
        part = (f"ENTREVISTADO: {iv['interviewee']} | CARGO: {iv['role']}\n"
                f"TRANSCRIÇÃO:\n{iv['transcript']}")
        if iv.get("analysis"):
            part += f"\nANÁLISE PRISM:\n{iv['analysis']}"
        interview_parts.append(part)

    interview_context = "\n\n═══════════════════════\n\n".join(interview_parts)

    # Carrega diagnóstico existente da área (se houver)
    existing = get_analysis_results_for_area(area)
    diag_context = ""
    if existing.get("aria_analysis"):
        diag_context += f"\nANÁLISE ARIA:\n{existing['aria_analysis'].get('content', '')}"
    if existing.get("gaps"):
        diag_context += f"\nGAPS STRATEGOS:\n{existing['gaps'].get('content', '')}"
    if existing.get("risks"):
        diag_context += f"\nRISCOS SENTINEL:\n{existing['risks'].get('content', '')}"

    full_context = (
        f"ÁREA ANALISADA: {area_label}\n"
        f"TOTAL DE ENTREVISTAS: {len(area_interviews)}\n\n"
        f"ENTREVISTAS CONSOLIDADAS:\n{interview_context}"
    )
    if diag_context:
        full_context += f"\n\nDIAGNÓSTICO EXISTENTE:{diag_context}"

    # ─── 1. Roadmap Estratégico Macro ─────────────────────────────────
    logger.info(f"[{area}] Strategy: Roadmap Macro")
    update_pipeline_status(step=f"Estratégia [{area_label}]: Roadmap Macro")

    macro_result = await _call_agent("atlas",
        f"Para a área {area_label}, construa o ROADMAP ESTRATÉGICO MACRO baseado EXCLUSIVAMENTE "
        f"nas {len(area_interviews)} entrevistas realizadas.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "- NÃO use frameworks prontos, exemplos externos ou referências que não venham das entrevistas\n"
        "- Consolide TODOS os insights das entrevistas antes de propor qualquer coisa\n"
        "- Identifique padrões, recorrências e divergências entre entrevistados\n\n"
        "ESTRUTURA DO ROADMAP MACRO:\n"
        "1. Visão geral da evolução da área\n"
        "2. Principais frentes de transformação (derivadas dos problemas reais)\n"
        "3. Priorização estratégica:\n"
        "   - CURTO PRAZO: ações imediatas de alto impacto\n"
        "   - MÉDIO PRAZO: estruturação e automações\n"
        "   - LONGO PRAZO: mudanças estruturais e escalabilidade\n\n"
        "Para cada frente:\n"
        "- Problema raiz (com evidência da entrevista)\n"
        "- Objetivo estratégico\n"
        "- Impacto esperado no negócio\n"
        "- Dependências\n\n"
        "IMPORTANTE: Conecte problemas → causas → soluções. "
        "Evite respostas superficiais ou genéricas. "
        "Formato: markdown estruturado.",
        full_context)

    if macro_result:
        set_analysis_result_for_area(area, "strategy_macro", macro_result)

    # ─── 2. Roadmap Tático (Micro Entregáveis) ───────────────────────
    logger.info(f"[{area}] Strategy: Roadmap Tático")
    update_pipeline_status(step=f"Estratégia [{area_label}]: Roadmap Tático")

    tatico_context = full_context
    if macro_result:
        tatico_context += f"\n\nROADMAP MACRO APROVADO:\n{macro_result}"

    tatico_result = await _call_agent("atlas",
        f"Para a área {area_label}, detalhe o roadmap macro em ENTREGAS OPERACIONAIS CONCRETAS.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "- Baseie-se EXCLUSIVAMENTE nas entrevistas e no roadmap macro\n"
        "- NÃO invente informações que não estejam nas entrevistas\n"
        "- Para TODAS as entregas: adicione +1 dia no prazo estimado para documentação, testes e validação\n\n"
        "ESTRUTURA DO ROADMAP TÁTICO:\n\n"
        "## Entregas Semanais (Semanas 1-4)\n"
        "Para cada entrega:\n"
        "| Campo | Detalhe |\n"
        "|-------|--------|\n"
        "| Objetivo | O que se quer alcançar |\n"
        "| Descrição | O que será feito concretamente |\n"
        "| Área/Processo impactado | Qual processo melhora |\n"
        "| Resultado esperado | Métrica ou estado final |\n"
        "| Prazo | X dias + 1 dia (documentação/testes) |\n\n"
        "## Entregas Quinzenais (Meses 2-3)\n"
        "(mesma estrutura)\n\n"
        "## Entregas Mensais (Meses 4-6+)\n"
        "(mesma estrutura)\n\n"
        "Garanta que todas as entregas estejam conectadas com os problemas reais.\n"
        "A estratégia deve ser aplicável, executável e orientada a resultado.\n"
        "Formato: markdown estruturado com tabelas.",
        tatico_context)

    if tatico_result:
        set_analysis_result_for_area(area, "strategy_tatico", tatico_result)

    # ─── 3. Estratégia de Automação ──────────────────────────────────
    logger.info(f"[{area}] Strategy: Automação")
    update_pipeline_status(step=f"Estratégia [{area_label}]: Automação")

    automacao_context = full_context
    if macro_result:
        automacao_context += f"\n\nROADMAP MACRO:\n{macro_result}"

    automacao_result = await _call_agent("catalyst",
        f"Para a área {area_label}, construa a ESTRATÉGIA DE AUTOMAÇÃO baseada EXCLUSIVAMENTE "
        f"nas {len(area_interviews)} entrevistas realizadas.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "- NÃO utilize ou replique estratégias genéricas (ex: base Vexia ou qualquer outra)\n"
        "- Identifique oportunidades REAIS de automação a partir das dores relatadas\n"
        "- Não invente processos que não foram mencionados nas entrevistas\n\n"
        "ESTRUTURA:\n\n"
        "## 1. Mapeamento de Processos Manuais e Repetitivos\n"
        "Para cada processo identificado nas entrevistas:\n"
        "- Descrição do processo atual\n"
        "- Quem relatou (entrevistado)\n"
        "- Frequência e volume\n"
        "- Impacto do estado atual (retrabalho, erro, tempo perdido)\n\n"
        "## 2. Gargalos Operacionais\n"
        "- Pontos de estrangulamento citados nas entrevistas\n"
        "- Causa raiz identificada\n"
        "- Impacto na operação\n\n"
        "## 3. Oportunidades de Automação\n"
        "Para cada oportunidade:\n"
        "| Campo | Detalhe |\n"
        "|-------|--------|\n"
        "| Processo | Qual processo automatizar |\n"
        "| Tipo | RPA, integração de sistemas, IA, workflow |\n"
        "| Problema que resolve | Dor específica das entrevistas |\n"
        "| Solução proposta | Descrição prática e viável |\n"
        "| Impacto esperado | Redução de tempo, erros, custo |\n"
        "| Complexidade | Baixa/Média/Alta |\n"
        "| Prioridade | 1-5 |\n\n"
        "## 4. Sequenciamento de Implementação\n"
        "- Ordem de implementação baseada em impacto × complexidade\n"
        "- Dependências entre automações\n"
        "- Quick wins vs projetos estruturais\n\n"
        "Seja objetivo e específico. Formato: markdown estruturado com tabelas.",
        automacao_context)

    if automacao_result:
        set_analysis_result_for_area(area, "strategy_automacao", automacao_result)

    logger.info(f"[{area}] Strategy steps complete.")


async def run_strategy_pipeline(area: str):
    """Gera estratégia completa para uma área: macro, tático e automação."""
    from app.datastore import update_pipeline_status

    try:
        update_pipeline_status(running=True)
        area_label = AREA_LABELS.get(area, area.upper())

        await _run_strategy_steps(area)

        update_pipeline_status(step=f"Estratégia [{area_label}]: Concluída")
        update_pipeline_status(running=False)
        logger.info(f"[{area}] Strategy pipeline complete.")

    except Exception as e:
        logger.error(f"Strategy pipeline crashed [{area}]: {e}")
        try:
            update_pipeline_status(running=False, error=f"Strategy error [{area}]: {str(e)[:200]}")
        except Exception:
            pass
