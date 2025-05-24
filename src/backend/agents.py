from src.backend.utils import get_transcript, get_summary

async def process_video(url: str):
    try:
        transcript = get_transcript(url)
        summary = get_summary(transcript)
        return {
            "transcript": transcript,
            "summary": summary
        }
    except Exception as e:
        print("❌ Agent Error:", e)
        raise
