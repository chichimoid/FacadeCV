from torch import device, cuda

class DeviceService:
    def __init__(self):
        self.device = device("cuda" if cuda.is_available() else "cpu")

    def get_device(self):
        if device is None:
            raise Exception("No device found")

        return self.device