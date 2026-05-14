import torch
from torch import nn
from torchvision import models

from src.services.device_service import DeviceService
from src.storage import file_storage

class Classifier:

    def __init__(self, device_service: DeviceService) -> None:
        self.classes = [
            "Нарушения не обнаружены",
            "Наличие подтоплений.",
            "Наличие сухостойных деревьев (только деревья)",
            "Нарушение содержания объектов ЦОДД.",
            "Нарушение содержания объектов Гормост.",
            "Нарушение содержания фасадов нежилых зданий и сооружений.",
            "Нарушение состояния фасада жилых зданий",
            "Нарушение содержания дорог, МАФов, остановочных павильонов, опор УНО, опор Мосгортранс.",
            "Неудовлетворительное содержание ОЛХ."
            ]

        self.device = device_service.get_device()

        model = torch.jit.load(file_storage.get_main_model(), map_location=self.device)
        model.to(self.device)
        model.eval()

        self.model = model


    def predict_batch(self, x: torch.Tensor) -> torch.Tensor:
        x = x.to(self.device)
        out = self.model(x)

        return torch.softmax(out, dim=1).cpu()