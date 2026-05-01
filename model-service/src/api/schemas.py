from typing import List, Dict
from pydantic import BaseModel

class JobCreateResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    total_images: int
    processed_images: int
    error: str = None

class ImagePrediction(BaseModel):
    image: str
    predictions: Dict[str, float]

class JobResultResponse(BaseModel):
    job_id: str
    status: str
    result: List[ImagePrediction]