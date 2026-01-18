import logging
import re
from typing import Union, Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from app.models import TranscriptResponse, SummaryResponse, ErrorResponse
from app.services.cache_manager import cache_manager
from app.services.subtitle_extractor import (
    subtitle_extractor,
    InvalidURLError,
    NoSubtitlesFoundError,
    TimeoutError as SubtitleTimeoutError,
    SubtitleExtractionError
)
from app.services.summarizer import (
    summarizer,
    CopilotNotFoundError,
    CopilotTimeoutError,
    InvalidSummaryLengthError,
    SummarizationFailedError
)
from app.parsers.vtt_parser import segments_to_plain_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/transcript",
    response_model=None,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL or summary length"},
        404: {"model": ErrorResponse, "description": "No subtitles found"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        503: {"model": ErrorResponse, "description": "GitHub Copilot CLI not available"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_transcript(
    url: str = Query(..., description="YouTube URL or video ID"),
    lang: str = Query("en", description="Language code (e.g., 'en', 'es', 'fr')"),
    format: str = Query("json", description="Response format: 'json' or 'text'"),
    timestamps: bool = Query(True, description="Include timestamps (only for JSON format)"),
    summary: Optional[Literal["short", "medium", "long"]] = Query(
        None,
        description="Generate summary instead of full transcript. Options: 'short', 'medium', 'long'"
    )
) -> Union[TranscriptResponse, SummaryResponse, PlainTextResponse]:
    """
    Get transcript for a YouTube video, or generate a summary.

    Returns transcript segments with timing information, plain text, or a summary.
    """
    try:
        # Validate language code FIRST (before any service calls)
        # IETF BCP 47 format: 2-3 letters, optionally followed by region/script code
        if not re.match(r'^[a-z]{2,3}(-[A-Za-z]{2,4})?$', lang):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid language code: {lang}. Must be ISO 639 format (e.g., 'en', 'en-US', 'pt-BR')"
            )

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

        # If summary is requested, generate/retrieve summary
        if summary:
            # Check summary cache first
            cached_summary = cache_manager.get_summary(video_id, lang, summary)
            if cached_summary:
                logger.info(f"Serving summary from cache: {video_id} ({lang}, {summary})")
                summary_text = cached_summary
            else:
                # Generate summary using Copilot CLI
                transcript_text = segments_to_plain_text(segments)

                # Validate transcript length before expensive summarization
                if len(transcript_text) > config.MAX_TRANSCRIPT_LENGTH:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Transcript too long ({len(transcript_text):,} characters). Maximum: {config.MAX_TRANSCRIPT_LENGTH:,}"
                    )

                logger.info(f"Generating summary: {video_id} ({lang}, {summary})")
                summary_text = await summarizer.summarize(transcript_text, summary)

                # Cache the summary
                cache_manager.set_summary(video_id, lang, summary, summary_text, is_generated)

            # Return summary based on format
            if format.lower() == "text":
                return PlainTextResponse(content=summary_text)
            else:
                return SummaryResponse(
                    video_id=video_id,
                    language=lang,
                    summary_length=summary,
                    summary=summary_text,
                    is_generated=is_generated
                )

        # Return transcript (no summary requested)
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

    except HTTPException:
        # Re-raise HTTP exceptions (including our validation errors) - MUST BE FIRST
        raise

    except ValueError as e:
        # Validation errors from cache_manager or other services
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except InvalidURLError as e:
        logger.warning(f"Invalid URL: {url}")
        raise HTTPException(status_code=400, detail=str(e))

    except InvalidSummaryLengthError as e:
        logger.warning(f"Invalid summary length: {summary}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoSubtitlesFoundError as e:
        logger.warning(f"No subtitles found: {url} ({lang})")
        raise HTTPException(status_code=404, detail=str(e))

    except SubtitleTimeoutError as e:
        logger.error(f"Timeout extracting subtitles: {url}")
        raise HTTPException(status_code=408, detail=str(e))

    except CopilotTimeoutError as e:
        logger.error(f"Timeout generating summary: {url}")
        raise HTTPException(status_code=408, detail=str(e))

    except CopilotNotFoundError as e:
        logger.error(f"GitHub Copilot CLI not available: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    except SummarizationFailedError as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

    except SubtitleExtractionError as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract subtitles: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
