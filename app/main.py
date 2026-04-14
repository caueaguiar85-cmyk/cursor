"""
AI Supply Chain API - Santista
Backend FastAPI com endpoints de Forecast, Inventory e Pricing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import List, Optional
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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
