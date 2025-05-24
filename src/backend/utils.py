import os
from openai import OpenAI
import yt_dlp
from dotenv import load_dotenv
import logging
import re
import tempfile

load_dotenv()

def get_openai_client():
    """Initialize OpenAI client with proper error handling"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)

def clean_transcript(text: str) -> str:
    """Clean SRT transcript text by removing timestamps and formatting"""
    # Remove SRT timestamps and sequence numbers
    text = re.sub(r'\d+\n', '', text)  # Remove sequence numbers
    text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', text)  # Remove timestamps
    text = re.sub(r'\n+', ' ', text)  # Replace multiple newlines with space
    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
    text = text.strip()
    return text

def get_transcript(url: str) -> str:
    try:
        logging.info(f"Starting transcript extraction for: {url}")
        
        # Configure yt-dlp options for better success rate
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en.*'],  # Match any English variant
            'subtitlesformat': 'srt/vtt/best',
            'skip_download': True,
            'quiet': False,  # Enable some logging for debugging
            'no_warnings': False,
            'extract_flat': False,
            'ignoreerrors': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            try:
                logging.info("Extracting video information...")
                info = ydl.extract_info(url, download=False)
                logging.info(f"Video title: {info.get('title', 'Unknown')}")
                logging.info(f"Video duration: {info.get('duration', 'Unknown')} seconds")
            except Exception as e:
                error_msg = str(e).lower()
                logging.error(f"Failed to extract video info: {e}")
                
                if "private video" in error_msg:
                    raise ValueError("This video is private and cannot be accessed.")
                elif "video unavailable" in error_msg or "unavailable" in error_msg:
                    raise ValueError("This video is no longer available.")
                elif "age-restricted" in error_msg or "age restricted" in error_msg:
                    raise ValueError("This video is age-restricted and cannot be processed.")
                elif "not available" in error_msg:
                    raise ValueError("This video is not available in your region or has been removed.")
                elif "blocked" in error_msg:
                    raise ValueError("This video is blocked and cannot be accessed.")
                else:
                    raise ValueError(f"Could not access video: {str(e)}")
            
            # Check available subtitles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            logging.info(f"Available manual subtitles: {list(subtitles.keys())}")
            logging.info(f"Available automatic captions: {list(automatic_captions.keys())}")
            
            # Try to download subtitles using yt-dlp's built-in functionality
            transcript_text = None
            
            # Create a temporary directory for subtitle downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                download_opts = {
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU'],
                    'subtitlesformat': 'srt',
                    'skip_download': True,
                    'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
                    'quiet': True,
                }
                
                try:
                    with yt_dlp.YoutubeDL(download_opts) as dl:
                        dl.download([url])
                        
                        # Look for downloaded subtitle files
                        import os
                        for file in os.listdir(temp_dir):
                            if file.endswith('.srt'):
                                logging.info(f"Found subtitle file: {file}")
                                with open(os.path.join(temp_dir, file), 'r', encoding='utf-8') as f:
                                    transcript_text = f.read()
                                break
                except Exception as e:
                    logging.warning(f"Failed to download subtitles: {e}")
            
            # If downloading failed, try direct URL access
            if not transcript_text:
                logging.info("Trying direct URL access for subtitles...")
                
                # Try manual subtitles first
                for lang in ['en', 'en-US', 'en-GB', 'en-CA']:
                    if lang in subtitles:
                        try:
                            subtitle_info = subtitles[lang]
                            if subtitle_info:
                                for sub in subtitle_info:
                                    if sub.get('ext') in ['srt', 'vtt']:
                                        subtitle_url = sub.get('url')
                                        if subtitle_url:
                                            logging.info(f"Trying to fetch {lang} manual subtitles from URL")
                                            import urllib.request
                                            response = urllib.request.urlopen(subtitle_url)
                                            transcript_text = response.read().decode('utf-8')
                                            logging.info(f"Successfully got manual subtitles in {lang}")
                                            break
                                if transcript_text:
                                    break
                        except Exception as e:
                            logging.warning(f"Failed to get manual subtitles for {lang}: {e}")
                            continue
                
                # If no manual subtitles, try automatic captions
                if not transcript_text:
                    logging.info("Trying automatic captions...")
                    for lang in ['en', 'en-US', 'en-GB']:
                        if lang in automatic_captions:
                            try:
                                subtitle_info = automatic_captions[lang]
                                if subtitle_info:
                                    for sub in subtitle_info:
                                        if sub.get('ext') in ['srt', 'vtt']:
                                            subtitle_url = sub.get('url')
                                            if subtitle_url:
                                                logging.info(f"Trying to fetch {lang} auto captions from URL")
                                                import urllib.request
                                                response = urllib.request.urlopen(subtitle_url)
                                                transcript_text = response.read().decode('utf-8')
                                                logging.info(f"Successfully got auto captions in {lang}")
                                                break
                                    if transcript_text:
                                        break
                            except Exception as e:
                                logging.warning(f"Failed to get auto captions for {lang}: {e}")
                                continue
            
            if not transcript_text:
                available_langs = list(subtitles.keys()) + list(automatic_captions.keys())
                if available_langs:
                    raise ValueError(f"No English captions available. Available languages: {', '.join(available_langs)}")
                else:
                    raise ValueError("No captions available for this video. The video may not have subtitles.")
            
            # Clean the transcript
            logging.info("Cleaning transcript...")
            cleaned_transcript = clean_transcript(transcript_text)
            
            if not cleaned_transcript or len(cleaned_transcript.strip()) < 10:
                raise ValueError("Retrieved transcript is empty or too short.")
            
            logging.info(f"Successfully extracted transcript ({len(cleaned_transcript)} characters)")
            return cleaned_transcript
            
    except ValueError:
        # Re-raise ValueError exceptions as they contain user-friendly messages
        raise
    except Exception as e:
        logging.error(f"Unexpected error getting transcript for {url}: {str(e)}")
        raise ValueError(f"Could not process video: {str(e)}")

def get_summary(transcript: str) -> str:
    try:
        client = get_openai_client()
        
        # Truncate transcript if it's too long (GPT-4 has token limits)
        max_chars = 8000  # Conservative limit
        if len(transcript) > max_chars:
            transcript = transcript[:max_chars] + "... [transcript truncated]"
        
        response = client.chat.completions.create(
        model="gpt-4",
        messages=[
                {"role": "system", "content": "You are a helpful summarizer. Create a concise but comprehensive summary of the video transcript."},
                {"role": "user", "content": f"Summarize this video transcript:\n\n{transcript}"}
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        if "OpenAI API key not configured" in str(e):
            raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        elif "insufficient_quota" in str(e) or "quota" in str(e).lower():
            raise ValueError("OpenAI API quota exceeded. Please try again later.")
        elif "invalid_api_key" in str(e) or "authentication" in str(e).lower():
            raise ValueError("OpenAI API authentication failed. Please check your API key.")
        else:
            raise ValueError(f"Could not generate summary: {str(e)}")
