from fastapi import File, UploadFile, HTTPException, APIRouter, Depends
from fastapi.responses import StreamingResponse

from src.storage.job_storage import JobStatus
from src.api.schemas import JobCreateResponse, JobStatusResponse, JobResultResponse
from src.storage.file_storage import save_job_files
from src.dependencies import get_job_storage

import asyncio
import json

import os

is_prod = os.getenv("ENV") == "production"

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/internal/jobs", response_model=JobCreateResponse)
async def create_job(files: list[UploadFile] = File(...), job_storage=Depends(get_job_storage)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")

    job = job_storage.create_job(
        image_count=len(files),
        payload={"image_paths": []},
    )

    image_paths = await save_job_files(job.job_id, files)

    job_storage.update_payload(
        job.job_id,
        {"image_paths": image_paths},
    )

    job_storage.queue_job(job.job_id)

    return {"job_id": job.job_id, "status": job.status.value}

@router.get("/internal/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, job_storage=Depends(get_job_storage)):
    job = job_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "total_images": job.total_images,
        "processed_images": job.processed_images,
        "error": job.error,
    }

@router.get("/internal/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str, job_storage=Depends(get_job_storage)):
    job = job_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Job is not completed yet")

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "result": job.result or [],
    }

@router.get("/internal/jobs/{job_id}/events")
async def stream_job_events(job_id: str, job_storage=Depends(get_job_storage)):
    job = job_storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_index = 0

        while True:
            current_job = job_storage.get_job(job_id)
            if current_job is None:
                break

            events, last_index = job_storage.pop_events_since(job_id, last_index)

            for evt in events:
                yield f"event: {evt.event}\n"
                yield f"data: {json.dumps(evt.data, ensure_ascii=False)}\n\n"

            if current_job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and not events:
                break

            yield ": keep-alive\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )