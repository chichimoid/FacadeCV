from fastapi import FastAPI

from src.storage.job_storage import JobStorage
from src.services.job_processer import JobProcesser
from src.services.classifier import Classifier
from src.services.device_service import DeviceService
from src.api.router import router
from src import config

is_prod = config.ENV == "production"
app = FastAPI(
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

job_storage = JobStorage()
deviceService = DeviceService()
classifier = Classifier(device_service=deviceService)
runner = JobProcesser(job_storage=job_storage, classifier=classifier, batch_size=32)

app.state.job_storage = job_storage # придумать что-то менее странное
app.include_router(router)

@app.on_event("startup")
def startup_event() -> None:
    runner.start()