import uvicorn
from .main import app

def main() -> None:
    """Entry point for running the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)
