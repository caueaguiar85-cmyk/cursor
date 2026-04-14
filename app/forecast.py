"""
Módulo de previsão de demanda
Usa Prophet se disponível; fallback com média ponderada exponencial.

Parâmetros calibrados para a realidade da Santista (reunião 10/04/2026):
  - Absenteísmo histórico de até 6% (reduzido para 3% com bônus de assiduidade)
  - Safety factor elevado para compensar risco operacional de paradas de linha
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────
FORECAST_DAYS    = 30
SAFETY_FACTOR    = 1.30    # 1.20 base + 0.10 pelo risco de absenteísmo (até 6%)
ABSENTEEISM_RISK = 0.06    # absenteísmo máximo histórico — usado no buffer
TREND_WINDOW     = 3       # últimos N períodos para calcular tendência

# Clientes estratégicos — disparam alerta em nível ATENÇÃO (não só CRÍTICO)
CLIENTES_PRIORITARIOS = ["p&g", "procter", "vf corporation", "vf corp"]


def run_forecast(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Retorna previsão de demanda para cada SKU.
    Em produção, substitua a lógica de 'fallback' por chamada ao Prophet
    com histórico real puxado de uma tabela de séries temporais.
    """
    results = []

    for item in items:
        sku    = item["sku"]
        client = item["client"]
        sales  = float(item["sales"])
        stock  = float(item["stock"])

        # —— Previsão: média diária × dias × fator de segurança ————————————
        # Safety factor de 1.30 absorve absenteísmo e microparalisações
        daily_avg     = sales / 30 if sales > 0 else 0
        forecast_30d  = round(daily_avg * FORECAST_DAYS * SAFETY_FACTOR, 2)
        days_of_stock = round(stock / daily_avg, 1) if daily_avg > 0 else 999

        # —— Verifica se é cliente estratégico ——————————————————————————
        is_priority = any(c in client.lower() for c in CLIENTES_PRIORITARIOS)

        # —— Classificação de risco ————————————————————————————————————
        # Clientes prioritários (P&G, VF Corp): eleva ATENÇÃO para CRÍTICO
        if days_of_stock < 7:
            risk = "CRÍTICO"
        elif days_of_stock < 15:
            risk = "CRÍTICO" if is_priority else "ATENÇÃO"
        else:
            risk = "OK"

        results.append({
            "sku":           sku,
            "client":        client,
            "forecast_30d":  forecast_30d,
            "daily_avg":     round(daily_avg, 2),
            "days_of_stock": days_of_stock,
            "risk":          risk,
            "is_priority":   is_priority,
        })

        logger.debug(f"Forecast SKU {sku}: {forecast_30d} un/30d | risco={risk} | prioritário={is_priority}")

    return results
