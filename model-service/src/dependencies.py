from fastapi import Request

def get_job_storage(request: Request):
    return request.app.state.job_storage