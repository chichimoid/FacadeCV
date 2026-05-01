from fastapi import APIRouter

from typing import List

import httpx
from fastapi import File, Request, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.clients.model_client import ModelClient

from src import config

router = APIRouter()
templates = Jinja2Templates(directory="src/api/templates")
model_client = ModelClient(config.MODEL_SERVICE_URL)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

@router.post("/submit")
async def submit_from_form(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    outgoing = []
    for idx, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")

        content = await file.read()
        outgoing.append(
            (
                file.filename or f"image_{idx}.jpg",
                content,
                file.content_type,
            )
        )

    created = await model_client.create_job(outgoing)
    return RedirectResponse(url=f"/jobs/{created['job_id']}/view", status_code=303)

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        return await model_client.get_job(job_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Model service error: {exc}") from exc


@router.get("/jobs/{job_id}/result")
async def get_result(job_id: str):
    try:
        return await model_client.get_result(job_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Model service error: {exc}") from exc


@router.get("/jobs/{job_id}/events")
async def proxy_job_events(job_id: str):
    try:
        client, upstream = await model_client.stream_events(job_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Model service error: {exc}") from exc

    async def generator():
        try:
            async for line in upstream.aiter_lines():
                yield f"{line}\n"
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

@router.get("/jobs/{job_id}/view", response_class=HTMLResponse)
async def job_view(request: Request, job_id: str):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "job_id": job_id,
        },
    )