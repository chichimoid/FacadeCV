import torch
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, Resize, ToTensor, Normalize

import math
from threading import Thread

from src.storage.job_storage import JobStorage
from src.storage.job_storage import JobStatus
from src.services.classifier import Classifier

from src.storage.file_storage import cleanup_job_files

from typing import List
from torchvision.datasets import VisionDataset
from pathlib import Path
from PIL import Image

class LoaderDataset(VisionDataset):
    def __init__(self, image_paths: List[Path], transform = None) -> None:
        super().__init__(transform=transform)
        self.image_paths = image_paths
        self.transform = transform

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index):
        path = self.image_paths[index]
        image = Image.open(path).convert("RGB")

        if self.transform is not None:
            image = self.transform(image)

        return (image,)

class JobProcesser:
    def __init__(self, job_storage: JobStorage, classifier: Classifier, batch_size) -> None:
        self.job_storage = job_storage
        self.classifier = classifier
        self.batch_size = batch_size

    def start(self) -> None:
        worker = Thread(target=self._run_loop, daemon=True)
        worker.start()

    def _run_loop(self) -> None:
        q = self.job_storage.task_queue()
        while True:
            task = q.get()
            job_id = task["job_id"]
            job = self.job_storage.get_job(job_id)
            if job is None:
                continue
            try:
                self._process_job(job_id, job.payload)
            except Exception as exc:
                raise exc
            finally:
                cleanup_job_files(job_id)
                q.task_done()

    def _process_job(self, job_id: str, payload: dict) -> None:
        image_paths: List[Path] = payload["image_paths"]
        total_images = len(image_paths)
        total_batches = max(1, math.ceil(total_images / self.batch_size))

        self.job_storage.update_job(
            job_id,
            progress=5,
            message="Preparing batch",
            processed_images=0,
        )

        transform = Compose([Resize((384, 384)),
                             ToTensor(),
                             Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

        ds = LoaderDataset(image_paths, transform=transform)

        loader = DataLoader(ds, batch_size=self.batch_size, shuffle=False)

        all_probs = []

        with torch.no_grad():
            for batch_idx, (x,) in enumerate(loader):
                start = batch_idx * self.batch_size
                end = start + self.batch_size

                self.job_storage.update_job(
                    job_id,
                    status=JobStatus.RUNNING,
                    progress=10 + int(80 * batch_idx / total_batches),
                    message=f"Running batch {batch_idx + 1}/{total_batches}",
                    processed_images=start,
                )

                out = self.classifier.predict_batch(x)
                all_probs.append(out)

                processed = min(end, total_images)
                self.job_storage.update_job(
                    job_id,
                    progress=10 + int(70 * (batch_idx + 1) / total_batches),
                    message=f"Processed {processed}/{total_images} images",
                    processed_images=processed,
                )

            self.job_storage.update_job(
                job_id,
                progress=95,
                message="Aggregating predictions",
                processed_images=total_images,
            )

        all_probs = torch.cat(all_probs).float().numpy()

        image_names = [path.name for path in image_paths]
        preds = [dict(zip(self.classifier.classes, probs)) for probs in all_probs]

        result = [{"image": img, "predictions": pred} for img, pred in zip(image_names, preds)]

        self.job_storage.complete_job(job_id, result)