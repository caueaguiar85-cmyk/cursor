"""
Módulo de gestão de inventário
Calcula ponto de reposição, estoque de segurança e status de cada SKU.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# ─── Parâmetros ───────────────────────────────────────────────────────────────
LEAD_TIME_DAYS     = 7     # prazo médio de reposição do fornecedor (dias)
SERVICE_LEVEL_Z    = 1.65  # z-score para 95% de nível de serviço
EXCESS_MULTIPLIER  = 3.0   # estoque > 3× a média mensal → excesso


def run_inventory(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Para cada SKU calcula:
    - safety_stock:    estoque de segurança (z × desvio × √lead_time)
    - reorder_point:   ponto de disparo do pedido
    - inventory_status: EXCESSO | NORMAL | REPOSIÇÃO | CRÍTICO
    - suggested_order: quantidade sugerida de compra (se necessário)
    """
    results = []

    for item in items:
        sku     = item["sku"]
        client  = item["client"]
        sales   = float(item["sales"])
        stock   = float(item["stock"])
        cost    = float(item["cost"])

        daily_avg = sales / 30 if sales > 0 else 0

        # ── Sem histórico de vendas — não há como calcular ──────────────
        if daily_avg == 0:
            results.append({
                "sku":             sku,
                "client":          client,
                "safety_stock":    0,
                "reorder_point":   0,
                "inventory_status": "SEM DADOS",
                "suggested_order": 0,
                "stock_value_brl": round(stock * cost, 2),
                "excess_alert":    False,
            })
            logger.debug(f"Inventory SKU {sku}: sem vendas — status=SEM DADOS")
            continue

        # ── Desvio padrão estimado (±20% da média) ──────────────────────
        # Em produção: calcule com histórico real de vendas
        std_daily = daily_avg * 0.20

        # ── Fórmulas clássicas de gestão de estoque ─────────────────────
        safety_stock  = round(SERVICE_LEVEL_Z * std_daily * (LEAD_TIME_DAYS ** 0.5), 2)
        reorder_point = round((daily_avg * LEAD_TIME_DAYS) + safety_stock, 2)
        excess_limit  = round(daily_avg * 30 * EXCESS_MULTIPLIER, 2)

        # ── Status ───────────────────────────────────────────────────────
        if stock > excess_limit:
            status = "EXCESSO"
            suggested_order = 0
        elif stock <= reorder_point and stock > safety_stock:
            status = "REPOSIÇÃO"
            suggested_order = round((daily_avg * 30) - stock + safety_stock, 2)
        elif stock <= safety_stock:
            status = "CRÍTICO"
            suggested_order = round((daily_avg * 30) + safety_stock, 2)
        else:
            status = "NORMAL"
            suggested_order = 0

        # ── Valor imobilizado ────────────────────────────────────────────
        stock_value = round(stock * cost, 2)

        results.append({
            "sku":             sku,
            "client":          client,
            "safety_stock":    safety_stock,
            "reorder_point":   reorder_point,
            "inventory_status": status,
            "suggested_order": suggested_order,
            "stock_value_brl": stock_value,
            "excess_alert":    stock > excess_limit,
        })

        logger.debug(f"Inventory SKU {sku}: status={status} | sugestão={suggested_order}")

    return results
