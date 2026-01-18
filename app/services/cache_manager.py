import json
import logging
import re
from pathlib import Path
from typing import Optional, List
from app.config import config
from app.models import TranscriptSegment

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages filesystem caching of transcript data"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or config.CACHE_DIR
        self.enabled = config.CACHE_ENABLED

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _validate_cache_params(self, video_id: str, language: str):
        """Validate video_id and language to prevent path traversal attacks"""
        # YouTube video IDs are 11 characters: alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            raise ValueError(f"Invalid video_id format: {video_id}")

        # Language codes: IETF BCP 47 format (e.g., 'en', 'en-US', 'pt-BR', 'zh-CN')
        # Pattern: 2-3 lowercase letters, optionally followed by hyphen and 2-4 letter region/script code
        if not re.match(r'^[a-z]{2,3}(-[A-Za-z]{2,4})?$', language):
            raise ValueError(f"Invalid language code: {language}")

    def _get_cache_path(self, video_id: str, language: str) -> Path:
        """Generate cache file path for a video and language"""
        # Validate inputs to prevent path traversal
        self._validate_cache_params(video_id, language)

        filename = f"{video_id}_{language}.json"
        cache_path = self.cache_dir / filename

        # Extra safety: ensure resolved path is within cache_dir
        if not cache_path.resolve().is_relative_to(self.cache_dir.resolve()):
            raise ValueError("Path traversal attempt detected")

        return cache_path

    def _get_summary_cache_path(self, video_id: str, language: str, length: str) -> Path:
        """Generate cache file path for a summary"""
        # Validate inputs to prevent path traversal
        self._validate_cache_params(video_id, language)

        # Validate summary length
        if length not in ["short", "medium", "long"]:
            raise ValueError(f"Invalid summary length: {length}")

        filename = f"{video_id}_{language}_summary_{length}.json"
        cache_path = self.cache_dir / filename

        # Extra safety: ensure resolved path is within cache_dir
        if not cache_path.resolve().is_relative_to(self.cache_dir.resolve()):
            raise ValueError("Path traversal attempt detected")

        return cache_path

    def get(self, video_id: str, language: str) -> Optional[tuple[List[TranscriptSegment], bool]]:
        """
        Retrieve cached transcript segments.

        Args:
            video_id: YouTube video ID
            language: Language code

        Returns:
            Tuple of (segments, is_generated) if found, None otherwise
        """
        if not self.enabled:
            return None

        cache_path = self._get_cache_path(video_id, language)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {video_id}_{language}")
            return None

        try:
            with cache_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            segments = [TranscriptSegment(**seg) for seg in data['segments']]
            is_generated = data.get('is_generated', False)

            logger.info(f"Cache hit: {video_id}_{language}")
            return segments, is_generated

        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.warning(f"Failed to read cache for {video_id}_{language}: {e}")
            return None

    def set(self, video_id: str, language: str, segments: List[TranscriptSegment], is_generated: bool):
        """
        Store transcript segments in cache.

        Args:
            video_id: YouTube video ID
            language: Language code
            segments: List of transcript segments
            is_generated: Whether subtitles are auto-generated
        """
        if not self.enabled:
            return

        cache_path = self._get_cache_path(video_id, language)

        try:
            data = {
                'video_id': video_id,
                'language': language,
                'is_generated': is_generated,
                'segments': [seg.model_dump() for seg in segments]
            }

            # Atomic write: write to temp file then rename
            temp_path = cache_path.with_suffix('.tmp')
            with temp_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            temp_path.replace(cache_path)
            logger.info(f"Cached transcript: {video_id}_{language}")

        except IOError as e:
            logger.error(f"Failed to write cache for {video_id}_{language}: {e}")

    def get_summary(self, video_id: str, language: str, length: str) -> Optional[str]:
        """
        Retrieve cached summary.

        Args:
            video_id: YouTube video ID
            language: Language code
            length: Summary length ('short', 'medium', 'long')

        Returns:
            Summary text if found, None otherwise
        """
        if not config.SUMMARY_CACHE_ENABLED:
            return None

        cache_path = self._get_summary_cache_path(video_id, language, length)

        if not cache_path.exists():
            logger.debug(f"Summary cache miss: {video_id}_{language}_{length}")
            return None

        try:
            with cache_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            summary = data.get('summary_text')
            logger.info(f"Summary cache hit: {video_id}_{language}_{length}")
            return summary

        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.warning(f"Failed to read summary cache for {video_id}_{language}_{length}: {e}")
            return None

    def set_summary(self, video_id: str, language: str, length: str, summary: str, is_generated: bool):
        """
        Store summary in cache.

        Args:
            video_id: YouTube video ID
            language: Language code
            length: Summary length ('short', 'medium', 'long')
            summary: Summary text
            is_generated: Whether original subtitles were auto-generated
        """
        if not config.SUMMARY_CACHE_ENABLED:
            return

        cache_path = self._get_summary_cache_path(video_id, language, length)

        try:
            from datetime import datetime, timezone

            data = {
                'video_id': video_id,
                'language': language,
                'summary_length': length,
                'summary_text': summary,
                'is_generated': is_generated,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'model': config.COPILOT_MODEL
            }

            # Atomic write: write to temp file then rename
            temp_path = cache_path.with_suffix('.tmp')
            with temp_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            temp_path.replace(cache_path)
            logger.info(f"Cached summary: {video_id}_{language}_{length}")

        except IOError as e:
            logger.error(f"Failed to write summary cache for {video_id}_{language}_{length}: {e}")

    def clear(self, video_id: Optional[str] = None, language: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            video_id: If provided, clear only this video's cache
            language: If provided (with video_id), clear only this specific entry
        """
        if not self.enabled:
            return

        if video_id and language:
            # Clear specific entry
            cache_path = self._get_cache_path(video_id, language)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Cleared cache: {video_id}_{language}")

        elif video_id:
            # Clear all entries for a video
            pattern = f"{video_id}_*.json"
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
                logger.info(f"Cleared cache: {cache_file.name}")

        else:
            # Clear entire cache (including summaries)
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared entire cache")


# Global cache manager instance
cache_manager = CacheManager()
