from pathlib import Path
import shutil

from fastapi import UploadFile

ROOT = Path("data")
MODELS_ROOT = Path("models")
UPLOAD_ROOT = ROOT / "tmp_uploads"
MAIN_MODEL = "convnext_s_atomic_5.pth"

async def save_job_files(job_id: str, files: list[UploadFile]) -> list[Path]:
    job_dir = UPLOAD_ROOT / job_id / "input"
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []

    for idx, file in enumerate(files):
        path = job_dir / file.filename

        if path.exists():
            k = 0
            parent = path.parent
            stem = path.stem
            suffix = path.suffix
            while path.exists():
                k += 1
                path = parent / f"{stem}({k}){suffix}"

        content = await file.read()
        path.write_bytes(content)

        saved_paths.append(path)

    return saved_paths

def get_main_model() -> Path:
    return MODELS_ROOT / MAIN_MODEL

def cleanup_job_files(job_id: str) -> None:
    job_dir = UPLOAD_ROOT / job_id
    shutil.rmtree(job_dir, ignore_errors=True)