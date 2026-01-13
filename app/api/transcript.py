import logging
from typing import Union
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.models import TranscriptResponse, ErrorResponse
from app.services.cache_manager import cache_manager
from app.services.subtitle_extractor import (
    subtitle_extractor,
    InvalidURLError,
    NoSubtitlesFoundError,
    TimeoutError as SubtitleTimeoutError,
    SubtitleExtractionError
)
from app.parsers.vtt_parser import segments_to_plain_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/transcript",
    response_model=TranscriptResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        404: {"model": ErrorResponse, "description": "No subtitles found"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_transcript(
    url: str = Query(..., description="YouTube URL or video ID"),
    lang: str = Query("en", description="Language code (e.g., 'en', 'es', 'fr')"),
    format: str = Query("json", description="Response format: 'json' or 'text'"),
    timestamps: bool = Query(True, description="Include timestamps (only for JSON format)")
) -> Union[TranscriptResponse, PlainTextResponse]:
    """
    Get transcript for a YouTube video.

    Returns transcript segments with timing information or plain text.
    """
    try:
        # Extract video ID for caching
        video_id = subtitle_extractor._extract_video_id(url)

        # Check cache first
        cached = cache_manager.get(video_id, lang)
        if cached:
            segments, is_generated = cached
            logger.info(f"Serving from cache: {video_id} ({lang})")
        else:
            # Extract subtitles using yt-dlp
            segments, is_generated = await subtitle_extractor.extract_subtitles(url, lang)

            # Cache the result
            cache_manager.set(video_id, lang, segments, is_generated)

        # Return based on format
        if format.lower() == "text":
            text = segments_to_plain_text(segments)
            return PlainTextResponse(content=text)
        else:
            # Return JSON format (default)
            response = TranscriptResponse(
                video_id=video_id,
                language=lang,
                is_generated=is_generated,
                segments=segments if timestamps else []
            )

            # If timestamps are disabled, still return data but without segment details
            if not timestamps:
                # Return just the text concatenated
                text = segments_to_plain_text(segments)
                # Return simplified response - just include basic metadata
                response.segments = segments

            return response

    except InvalidURLError as e:
        logger.warning(f"Invalid URL: {url}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoSubtitlesFoundError as e:
        logger.warning(f"No subtitles found: {url} ({lang})")
        raise HTTPException(status_code=404, detail=str(e))

    except SubtitleTimeoutError as e:
        logger.error(f"Timeout extracting subtitles: {url}")
        raise HTTPException(status_code=408, detail=str(e))

    except SubtitleExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract subtitles: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
