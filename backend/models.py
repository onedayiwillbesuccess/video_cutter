from pydantic import BaseModel


class ClipResult(BaseModel):
    start_time: float
    end_time: float
    title: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    step: str
    progress: float
    message: str
    clips: list[ClipResult] = []
    output_dir: str = ""


class SubmitRequest(BaseModel):
    url: str
