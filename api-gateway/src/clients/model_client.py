import httpx

class ModelClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def create_job(self, files: list[tuple[str, bytes, str]]) -> dict:
        multipart = []
        for filename, content, content_type in files:
            multipart.append(
                ("files", (filename, content, content_type))
            )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/internal/jobs", files=multipart)
            response.raise_for_status()
            return response.json()

    async def get_job(self, job_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/internal/jobs/{job_id}")
            response.raise_for_status()
            return response.json()

    async def get_result(self, job_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/internal/jobs/{job_id}/result")
            response.raise_for_status()

            return response.json()

    async def stream_events(self, job_id: str):
        client = httpx.AsyncClient(timeout=None)
        request = client.build_request("GET", f"{self.base_url}/internal/jobs/{job_id}/events")
        response = await client.send(request, stream=True)
        response.raise_for_status()
        return client, response