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



@router.post("/shipment/{id}")
async def ingest_shipment_with_id(
    id: str,
    payload: Dict[str, Any] = payload_schema
):
    """Webhook endpoint to ingest shipment JSON with job id in path.

    - Ensures the payload contains the provided job id under `job._id`
    - Ensures the `jobs` array contains an entry for the job id (appends if missing)
    - Upserts shipment using Supabase
    """
    try:
        from services.supabase import supabase_service

        # Normalize job object
        job_obj = (payload.get("job") or {})

        # Ensure job._id matches the path id
        incoming_job_id = job_obj.get("_id")
        if incoming_job_id != id:
            logger.warning(f"job._id mismatch or missing; setting payload.job._id to path id {id}")
            job_obj["_id"] = id
            payload["job"] = job_obj

        # Ensure jobs array contains the job entry
        jobs_arr = payload.get("jobs")
        if not isinstance(jobs_arr, list):
            jobs_arr = []

        # Check if job already present in jobs list
        has_job = any(isinstance(j, dict) and j.get("_id") == id for j in jobs_arr)
        if not has_job:
            # Append full job object if available; otherwise append minimal stub
            if isinstance(job_obj, dict) and job_obj:
                jobs_arr.append(job_obj)
            else:
                jobs_arr.append({"_id": id})

        payload["jobs"] = jobs_arr

        # Upsert updated payload
        result = await supabase_service.upsert_shipment(payload)
        if not result.get("success"):
            logger.error(f"Failed to upsert shipment: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return JSONResponse({
            "success": True,
            "job_id": result.get("job_id") or id,
            "long_id": result.get("long_id"),
            "data_id": result.get("data_id"),
            "jobs_count": len(jobs_arr)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in shipment webhook with id")
        raise HTTPException(status_code=500, detail=str(e))
