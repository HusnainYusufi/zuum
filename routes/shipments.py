from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from .auth import get_current_user
from services.supabase import supabase_service

router = APIRouter(prefix="/{env}/shipments", tags=["shipments"])


def _validate_env(env: str) -> None:
    """Validate environment parameter."""
    allowed_envs = {"dev", "staging", "prod"}
    if env not in allowed_envs:
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid environment '{env}'. Must be one of: {', '.join(allowed_envs)}"
        )


@router.get("/search")
async def search_shipments(
    env: str,
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
    sort_dir: Optional[str] = Query("desc"),
    current_user: dict = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    _validate_env(env)

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
            "env": env,
            "limit": limit,
            "offset": offset,
            "sort_dir": (sort_dir or "desc").lower(),
        }

        result = await supabase_service.search_shipments(params)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid request"))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{job_id}")
async def get_shipment_data(env: str, job_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    _validate_env(env)

    try:
        result = await supabase_service.get_shipment_data(job_id, env)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


