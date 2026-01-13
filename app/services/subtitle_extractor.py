import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple
from app.config import config
from app.models import TranscriptSegment
from app.parsers.vtt_parser import parse_vtt

logger = logging.getLogger(__name__)


class SubtitleExtractionError(Exception):
    """Base exception for subtitle extraction errors"""
    pass


class NoSubtitlesFoundError(SubtitleExtractionError):
    """Raised when no subtitles are available for the video"""
    pass


class InvalidURLError(SubtitleExtractionError):
    """Raised when the provided URL is invalid"""
    pass


class TimeoutError(SubtitleExtractionError):
    """Raised when extraction times out"""
    pass


class SubtitleExtractor:
    """Handles subtitle extraction using yt-dlp"""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_PROCESSES)

    @staticmethod
    def _extract_video_id(url: str) -> str:
        """
        Extract YouTube video ID from URL or return as-is if already an ID.

        Args:
            url: YouTube URL or video ID

        Returns:
            Video ID

        Raises:
            InvalidURLError: If URL is invalid
        """
        # If it looks like a video ID (11 characters, alphanumeric), return it
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        # Extract from various YouTube URL formats
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise InvalidURLError(f"Could not extract video ID from URL: {url}")

    async def extract_subtitles(
        self,
        url: str,
        language: str = "en"
    ) -> Tuple[List[TranscriptSegment], bool]:
        """
        Extract subtitles from a YouTube video.

        Args:
            url: YouTube URL or video ID
            language: Language code (default: "en")

        Returns:
            Tuple of (segments, is_generated) where is_generated indicates
            if the subtitles are auto-generated

        Raises:
            InvalidURLError: If URL is invalid
            NoSubtitlesFoundError: If no subtitles are available
            TimeoutError: If extraction times out
            SubtitleExtractionError: For other extraction errors
        """
        async with self._semaphore:
            video_id = self._extract_video_id(url)
            logger.info(f"Extracting subtitles for video {video_id}, language: {language}")

            # Create temporary directory for yt-dlp output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                output_template = str(temp_path / "subtitle")

                # Build yt-dlp command
                cmd = [
                    "python",
                    "-m",
                    "yt_dlp",
                    "--write-subs",
                    "--write-auto-subs",
                    "--skip-download",
                    "--sub-langs", language,
                    "--sub-format", "vtt",
                    "-o", output_template,
                    f"https://www.youtube.com/watch?v={video_id}"
                ]

                try:
                    # Execute yt-dlp
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(),
                            timeout=config.YTDLP_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                        raise TimeoutError(f"Subtitle extraction timed out after {config.YTDLP_TIMEOUT}s")

                    if process.returncode != 0:
                        stderr_text = stderr.decode('utf-8', errors='replace')
                        logger.error(f"yt-dlp failed: {stderr_text}")

                        if "No video subtitles" in stderr_text or "no subtitles" in stderr_text.lower():
                            raise NoSubtitlesFoundError(f"No subtitles available for video {video_id} in language {language}")

                        raise SubtitleExtractionError(f"yt-dlp failed with return code {process.returncode}")

                    # Find the generated subtitle file
                    vtt_files = list(temp_path.glob("*.vtt"))

                    if not vtt_files:
                        raise NoSubtitlesFoundError(f"No subtitle files generated for video {video_id}")

                    # Determine if subtitles are auto-generated
                    # yt-dlp names auto-generated subs with language code like "en" and manual ones like "en.en"
                    # or includes "auto" in the filename
                    subtitle_file = vtt_files[0]
                    is_generated = "-auto" in subtitle_file.name or subtitle_file.stem.count('.') == 0

                    # Parse VTT file
                    vtt_content = subtitle_file.read_text(encoding='utf-8')
                    segments = parse_vtt(vtt_content)

                    logger.info(f"Successfully extracted {len(segments)} segments (auto-generated: {is_generated})")
                    return segments, is_generated

                except (InvalidURLError, NoSubtitlesFoundError, TimeoutError):
                    raise
                except Exception as e:
                    logger.exception(f"Unexpected error during subtitle extraction: {e}")
                    raise SubtitleExtractionError(f"Failed to extract subtitles: {str(e)}")


# Global extractor instance
subtitle_extractor = SubtitleExtractor()
