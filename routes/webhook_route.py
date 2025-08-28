from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from loguru import logger
from services.supabase import supabase_service

router = APIRouter(prefix="/webhook", tags=["webhook"])


payload_schema = Body(
    ...,
    description="Shipment payload as provided by Zuum export",
    example={
        "customerTenantId": "LNT_1",
        "loadId": 224,
        "job": {"_id": "6690e75db20ba727d428a143", "carrierId": "667170c6b77ccd0008930e69", "offer": "6690e75bb20ba727d428a136"},
    },
)


def _validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Basic validation/coercion for fields we rely on."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid payload format")
    # Work on a shallow copy to avoid mutating the original top-level dict
    payload = payload.copy()
    job = payload.get("job")
    if job is not None and not isinstance(job, dict):
        raise HTTPException(status_code=422, detail="Invalid job object")
    # Coerce identifiers to strings where applicable
    if isinstance(job, dict) and job.get("_id") is not None and not isinstance(job.get("_id"), str):
        # Replace nested job with a cloned mapping to avoid mutating the original
        payload["job"] = {**job, "_id": str(job.get("_id"))}
    return payload


@router.post("/shipment")
async def ingest_shipment(
    payload: Dict[str, Any] = payload_schema,
):
    """Webhook endpoint to ingest shipment JSON from external system.

    Expects a JSON body matching the sample schema in `shipment-es-sample.json`.
    """
    try:
        safe_payload = _validate_payload(payload.copy() if isinstance(payload, dict) else payload)
        # Enforce presence of job._id for this endpoint
        job_obj = safe_payload.get("job") if isinstance(safe_payload, dict) else None
        job_id = job_obj.get("_id") if isinstance(job_obj, dict) else None
        if not job_id:
            raise HTTPException(status_code=422, detail="job._id is required")

        result = await supabase_service.upsert_shipment(safe_payload)
        if not result.get("success"):
            logger.error(f"Failed to upsert shipment: {result.get('error')}")
            # Map missing job error to 422; otherwise 500
            if result.get("error") == "job._id is required for shipment upsert":
                raise HTTPException(status_code=422, detail="job._id is required")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return JSONResponse({"success": True, "job_id": result.get("job_id"), "updated_at": result.get("updated_at")})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in shipment webhook")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shipment/{id}")
async def ingest_shipment_with_id(
    id: str,
    payload: Dict[str, Any] = payload_schema,
):
    """Webhook endpoint to ingest shipment JSON with job id in path.

    - Ensures the payload contains the provided job id under `job._id`
    - Ensures the `jobs` array contains an entry for the job id (appends if missing)
    - Upserts shipment using Supabase
    """
    try:
        safe_payload = _validate_payload(payload.copy() if isinstance(payload, dict) else payload)

        # Normalize job object (clone before mutation to avoid leaking changes)
        job_obj = safe_payload.get("job") or {}
        if isinstance(job_obj, dict):
            job_obj = dict(job_obj)

        # Ensure job._id matches the path id
        incoming_job_id = job_obj.get("_id")
        if incoming_job_id != id:
            logger.warning(f"job._id mismatch or missing; setting payload.job._id to path id {id}")
            job_obj["_id"] = id
            safe_payload["job"] = job_obj

        # Ensure jobs array contains the job entry
        jobs_arr = safe_payload.get("jobs")
        if not isinstance(jobs_arr, list):
            jobs_arr = []
        else:
            jobs_arr = list(jobs_arr)

        # Check if job already present in jobs list
        has_job = any(isinstance(j, dict) and j.get("_id") == id for j in jobs_arr)
        if not has_job:
            # Append full job object if available; otherwise append minimal stub
            if isinstance(job_obj, dict) and job_obj:
                jobs_arr.append(job_obj)
            else:
                jobs_arr.append({"_id": id})

        safe_payload["jobs"] = jobs_arr

        # Upsert updated payload
        result = await supabase_service.upsert_shipment(safe_payload)
        if not result.get("success"):
            logger.error(f"Failed to upsert shipment: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

        return JSONResponse(
            {"success": True, "job_id": result.get("job_id") or id, "updated_at": result.get("updated_at"), "jobs_count": len(jobs_arr)}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in shipment webhook with id")
        raise HTTPException(status_code=500, detail=str(e))
