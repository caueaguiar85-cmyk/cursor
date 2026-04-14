"""
Módulo de precificação dinâmica
Sugere preço com base em custo, margem alvo, giro de estoque e posição competitiva.

Parâmetros calibrados para a realidade da Santista (reunião 10/04/2026):
  - CMV médio: R$ 12 | Preço de venda médio: R$ 15 — margem bruta ~20%
  - 70% do CMV composto por algodão, mão de obra e energia
  - Margem mínima conservadora dado ambiente competitivo (Paraguai, informais)
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ─── Parâmetros de margem — calibrados Santista ───────────────────────────────
TARGET_MARGIN       = 0.20   # margem bruta alvo (20% — realidade têxtil brasileira)
EXCESS_DISCOUNT     = 0.05   # desconto para girar estoque (conservador, margem apertada)
LOW_STOCK_PREMIUM   = 0.03   # prêmio de preço quando estoque está crítico
MIN_MARGIN          = 0.05   # margem mínima aceitável (piso de sobrevivência)


def run_pricing(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Para cada SKU retorna:
    - base_price:       preço com margem alvo
    - suggested_price:  preço ajustado por posição de estoque
    - margin_pct:       margem resultante
    - pricing_action:   MANTER | DESCONTO | PREMIUM | REVISAR
    """
    results = []

    for item in items:
        sku   = item["sku"]
        client = item["client"]
        sales  = float(item["sales"])
        stock  = float(item["stock"])
        cost   = float(item["cost"])

        if cost <= 0:
            logger.warning(f"SKU {sku}: custo zero — não é possível precificar")
            results.append({
                "sku":             sku,
                "client":          client,
                "cost":            cost,
                "base_price":      0,
                "suggested_price": 0,
                "margin_pct":      0,
                "coverage_months": 0,
                "pricing_action":  "REVISAR",
            })
            continue

        # —— Preço base pela margem alvo ———————————————————————————————
        base_price = round(cost / (1 - TARGET_MARGIN), 2)

        # —— Giro de estoque (meses de cobertura) ——————————————————————
        monthly_sales = sales
        coverage_months = (stock / monthly_sales) if monthly_sales > 0 else 99

        # —— Ajuste dinâmico ———————————————————————————————————————————
        if coverage_months > 3:
            # Estoque alto — aplica desconto para girar
            adjusted_price  = round(base_price * (1 - EXCESS_DISCOUNT), 2)
            pricing_action  = "DESCONTO"
        elif coverage_months < 0.5:
            # Estoque crítico — sobe preço levemente
            adjusted_price  = round(base_price * (1 + LOW_STOCK_PREMIUM), 2)
            pricing_action  = "PREMIUM"
        else:
            adjusted_price  = base_price
            pricing_action  = "MANTER"

        # —— Validação de margem mínima ————————————————————————————————
        floor_price = round(cost / (1 - MIN_MARGIN), 2)
        if adjusted_price < floor_price:
            adjusted_price = floor_price
            pricing_action = "REVISAR"  # abaixo do piso — sinalizar

        margin_pct = round((adjusted_price - cost) / adjusted_price * 100, 1)

        results.append({
            "sku":             sku,
            "client":          client,
            "cost":            cost,
            "base_price":      base_price,
            "suggested_price": adjusted_price,
            "margin_pct":      margin_pct,
            "coverage_months": round(coverage_months, 1),
            "pricing_action":  pricing_action,
        })

        logger.debug(f"Pricing SKU {sku}: {pricing_action} — R$ {adjusted_price} | margem {margin_pct}%")

    return results
