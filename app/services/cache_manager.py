import json
import logging
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

    def _get_cache_path(self, video_id: str, language: str) -> Path:
        """Generate cache file path for a video and language"""
        filename = f"{video_id}_{language}.json"
        return self.cache_dir / filename

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
            # Clear entire cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Cleared entire cache")


# Global cache manager instance
cache_manager = CacheManager()
