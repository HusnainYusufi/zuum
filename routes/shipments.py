from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from .auth import get_current_user
from services.supabase import supabase_service

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("/search")
async def search_shipments(
    tenant_id: Optional[str] = Query(None),
    shipment_id: Optional[str] = Query(None),
    load_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    fleet_phone: Optional[str] = Query(None),
    fleet_name: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    carrier_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:

        params: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "shipment_id": shipment_id,
            "load_id": load_id,
            "job_id": job_id,
            "fleet_phone": fleet_phone,
            "fleet_name": fleet_name,
            "customer_name": customer_name,
            "carrier_id": carrier_id,
            "limit": limit,
            "offset": offset,
        }

        result = await supabase_service.search_shipments(params)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid request"))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{data_id}")
async def get_shipment_data(data_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        from services.supabase import supabase_service

        result = await supabase_service.get_shipment_data(data_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


