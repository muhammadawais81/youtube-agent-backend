from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    url: str

class AnalyzeResponse(BaseModel):
    transcript: str
    summary: str
