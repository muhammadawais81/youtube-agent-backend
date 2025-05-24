from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .agents import process_video
from .schemas import AnalyzeRequest, AnalyzeResponse
import logging

# Error response models
class ErrorResponse(BaseModel):
    detail: str

app = FastAPI(
    title="YouTube Script Generator API",
    description="API for analyzing YouTube videos and generating transcripts and summaries",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler for 500 errors
@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred while processing the video. Please try again later."}
    )

@app.post(
    "/analyze", 
    response_model=AnalyzeResponse,
    responses={
        200: {
            "description": "Video analysis completed successfully",
            "model": AnalyzeResponse,
            "content": {
                "application/json": {
                    "example": {
                        "transcript": "Video transcript content...",
                        "summary": "Video summary content..."
                    }
                }
            }
        },
        400: {
            "description": "Bad Request - Invalid URL, video not available, or API quota issues",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_url": {"value": {"detail": "Video not found. Please check the URL."}},
                        "restricted_video": {"value": {"detail": "This video is private or restricted."}},
                        "no_captions": {"value": {"detail": "No captions available for this video."}},
                        "quota_exceeded": {"value": {"detail": "OpenAI API quota exceeded. Please try again later."}}
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error - An unexpected error occurred during video processing",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "An unexpected error occurred while processing the video. Please try again later."}
                }
            }
        }
    },
    summary="Analyze YouTube Video",
    description="Analyzes a YouTube video URL to extract transcript and generate a summary"
)
async def analyze_video(payload: AnalyzeRequest):
    try:
        return await process_video(payload.url)
    except ValueError as e:
        # These are expected errors (bad URL, no captions, API issues, etc.)
        logging.warning(f"Client error for video {payload.url}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors
        logging.error(f"Unexpected error processing video {payload.url}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing the video. Please try again later."
        )
