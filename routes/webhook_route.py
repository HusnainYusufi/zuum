from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from loguru import logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


payload_schema = Body(
    ...,
    description="Shipment payload as provided by Zuum export",
    example={
        "longId": "668d6d8be296715c0c2316aa",
        "customerTenantId": "LNT_1",
        "loadId": 224,
        "job": {
            "_id": "6690e75db20ba727d428a143",
            "carrierId": "667170c6b77ccd0008930e69",
            "offer": "6690e75bb20ba727d428a136"
        }
    },
)


@router.post("/shipment")
async def ingest_shipment(
    payload: Dict[str, Any] = payload_schema
):
    """Webhook endpoint to ingest shipment JSON from external system.

    Expects a JSON body matching the sample schema in `shipment-es-sample.json`.
    """
    try:
        from services.supabase import supabase_service

        result = await supabase_service.upsert_shipment(payload)
        if not result.get("success"):
            logger.error(f"Failed to upsert shipment: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return JSONResponse({"success": True, "shipment_long_id": result.get("long_id")})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in shipment webhook")
        raise HTTPException(status_code=500, detail=str(e))


