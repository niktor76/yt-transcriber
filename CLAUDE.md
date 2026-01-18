# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT:** Always read `MEMORY.md` first to understand the current work-in-progress and active problems.

## Project Overview

YouTube Transcript Service - A self-hosted FastAPI service that fetches YouTube transcripts using yt-dlp without third-party APIs. The service extracts subtitles (manual or auto-generated), caches them locally, and serves them via HTTP endpoints in JSON or plain text format.

## Development Commands

### Running the Server
```bash
# Start development server with auto-reload
uvicorn app.main:app --reload

# Start on custom host/port
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Or use the main module directly
python -m app.main
```

### Testing the API
```bash
# Health check
curl http://localhost:8000/health

# Get transcript (JSON with timestamps)
curl "http://localhost:8000/transcript?url=VIDEO_ID&lang=en"

# Get plain text transcript
curl "http://localhost:8000/transcript?url=VIDEO_ID&format=text"
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Flow
1. **API Request** (`app/api/transcript.py`) receives YouTube URL/ID
2. **Cache Check** (`app/services/cache_manager.py`) looks for cached transcript
3. **Subtitle Extraction** (`app/services/subtitle_extractor.py`) runs yt-dlp if cache miss
4. **VTT Parsing** (`app/parsers/vtt_parser.py`) converts VTT format to structured segments
5. **Cache Write** stores results for future requests
6. **Response** returns JSON or plain text based on format parameter

### Key Design Patterns

**yt-dlp Invocation**: The subtitle extractor uses `python -m yt_dlp` (not `yt-dlp` command) because yt-dlp may not be in system PATH on Windows. This is critical - changing to direct `yt-dlp` command will break on systems where it's not in PATH.

**Concurrency Control**: Uses asyncio.Semaphore to limit concurrent yt-dlp processes (default: 2). This prevents resource exhaustion since yt-dlp is CPU-intensive. The semaphore is in `SubtitleExtractor.__init__`.

**Atomic Cache Writes**: Cache manager writes to temporary file then renames (atomic operation) to prevent corrupted cache entries from partial writes during crashes or interruptions.

**Error Hierarchy**: Custom exceptions in `subtitle_extractor.py`:
- `InvalidURLError` → 400
- `NoSubtitlesFoundError` → 404
- `TimeoutError` → 408
- `SubtitleExtractionError` → 500

### Configuration

All configuration via environment variables in `app/config.py`:
- `CACHE_DIR` - where transcript JSON files are stored (default: `./cache`)
- `YTDLP_TIMEOUT` - subprocess timeout in seconds (default: 30)
- `MAX_CONCURRENT_PROCESSES` - semaphore limit (default: 2)
- `CACHE_ENABLED` - toggle caching on/off (default: true)

The `Config.initialize()` method creates the cache directory. This is called during FastAPI lifespan startup.

### Module Responsibilities

- `app/main.py` - FastAPI app, CORS, lifespan management, health endpoints
- `app/config.py` - Environment variable configuration with sensible defaults
- `app/models.py` - Pydantic models for validation and serialization
- `app/api/transcript.py` - Single GET endpoint that orchestrates cache/extract/parse
- `app/services/subtitle_extractor.py` - yt-dlp subprocess wrapper with video ID extraction
- `app/services/cache_manager.py` - Filesystem JSON cache with get/set/clear operations
- `app/parsers/vtt_parser.py` - Regex-based WebVTT parser that handles timestamps and VTT tags

### Data Flow Detail

**Cache Key Format**: `{video_id}_{language}.json` (e.g., `dQw4w9WgXcQ_en.json`)

**VTT Parsing**: The parser strips VTT tags like `<c>` and `<v>`, handles optional hour component in timestamps, and concatenates multi-line subtitle text within each cue.

**Subtitle Type Detection**: Auto-generated vs manual subtitles are detected by filename pattern from yt-dlp output. Files with `-auto` in the name or fewer dots in the stem indicate auto-generated.

## Important Notes

- **No video downloads**: yt-dlp is invoked with `--skip-download --write-subs --write-auto-subs` to fetch only subtitle files
- **Temporary directory cleanup**: yt-dlp outputs to Python tempfile.TemporaryDirectory which auto-cleans on context exit
- **URL sanitization**: Video IDs are extracted via regex patterns, preventing command injection since subprocess uses `shell=False`
- **Response format switching**: The same endpoint returns either Pydantic model (JSON) or PlainTextResponse based on `format` query parameter
