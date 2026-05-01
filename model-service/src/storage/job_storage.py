from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List
import queue
import uuid

from enum import Enum

@dataclass
class JobEvent:
    event: str
    data: Dict[str, Any]
    timestamp: str

@dataclass
class JobStatus(Enum):
    FAILED = "FAILED"
    INITIALIZING = "INITIALIZING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


@dataclass
class JobRecord:
    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = field(default_factory=lambda: JobStatus.INITIALIZING)
    progress: int = 0
    message: str = "Initializing job"
    total_images: int = 0
    processed_images: int = 0
    error: str = None
    result: List[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: List[JobEvent] = field(default_factory=list)


class JobStorage:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._task_queue: "queue.Queue[dict]" = queue.Queue()

    def create_job(self, image_count: int, payload: dict) -> JobRecord:
        job_id = str(uuid.uuid4())
        job = JobRecord(
            job_id=job_id,
            total_images=image_count,
            payload=payload,
            status=JobStatus.INITIALIZING,
            progress=0,
            message="Initializing job",
        )
        with self._lock:
            self._jobs[job_id] = job
            self._append_event_locked(
                job_id,
                event="job_created",
                data=self._public_status(job),
            )
        return job

    def queue_job(self, job_id: str) -> None:
        self.update_job(job_id=job_id, status=JobStatus.QUEUED, message="Queued")
        self._task_queue.put({"job_id": job_id})

    def update_payload(self, job_id: str, payload: dict) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.payload = payload
            job.updated_at = datetime.now(timezone.utc).isoformat()

    def get_job(self, job_id: str) -> JobRecord:
        with self._lock:
            return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return None if job is None else job.result

    def task_queue(self) -> "queue.Queue[dict]":
        return self._task_queue

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus = None,
        progress: int = None,
        message: str = None,
        processed_images: int = None,
        error: str = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if processed_images is not None:
                job.processed_images = processed_images
            if error is not None:
                job.error = error
            job.updated_at = datetime.now(timezone.utc).isoformat()

            self._append_event_locked(
                job_id,
                event="job_updated",
                data=self._public_status(job),
            )

    def complete_job(self, job_id: str, result: List[Dict[str, Any]]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.message = "Completed"
            job.processed_images = job.total_images
            job.result = result
            job.updated_at = datetime.now(timezone.utc).isoformat()

            self._append_event_locked(
                job_id,
                event="job_completed",
                data=self._public_status(job),
            )

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.message = "Failed"
            job.error = error
            job.updated_at = datetime.now(timezone.utc).isoformat()

            self._append_event_locked(
                job_id,
                event="job_failed",
                data=self._public_status(job),
            )

    def pop_events_since(self, job_id: str, last_index: int) -> tuple[list[JobEvent], int]:
        with self._lock:
            job = self._jobs[job_id]
            events = job.events[last_index:]
            return events, len(job.events)

    def _append_event_locked(self, job_id: str, event: str, data: Dict[str, Any]) -> None:
        job = self._jobs[job_id]
        job.events.append(
            JobEvent(
                event=event,
                data=data,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def _public_status(self, job: JobRecord) -> Dict[str, Any]:
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "message": job.message,
            "total_images": job.total_images,
            "processed_images": job.processed_images,
            "error": job.error,
        }