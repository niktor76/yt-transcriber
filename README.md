# YouTube Transcript Service

A self-hosted Python HTTP service using FastAPI and yt-dlp to fetch YouTube transcripts without third-party APIs.

## Features

- Fetch YouTube video transcripts by URL or video ID
- Support for multiple languages
- Automatic and manual subtitle support
- Response formats: JSON (with timestamps) or plain text
- Filesystem-based caching for improved performance
- Concurrency control to prevent resource exhaustion
- No video/audio downloads - subtitles only

## Requirements

- Python 3.11+
- yt-dlp (installed automatically with dependencies)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd yt-transcriber
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Create a `.env` file for custom configuration:
```bash
cp .env.example .env
```

## Usage

### Starting the Server

Run the server using uvicorn:

```bash
uvicorn app.main:app --reload
```

Or use the main module directly:

```bash
python -m app.main
```

The server will start on `http://127.0.0.1:8000` by default.

### API Endpoints

#### Get Transcript

**Endpoint:** `GET /transcript`

**Query Parameters:**
- `url` (required): YouTube URL or video ID
- `lang` (optional): Language code (default: `en`)
- `format` (optional): Response format - `json` or `text` (default: `json`)
- `timestamps` (optional): Include timestamps in JSON response (default: `true`)

**Examples:**

```bash
# Get transcript with video ID
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&lang=en"

# Get transcript with full URL
curl "http://localhost:8000/transcript?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Get plain text format
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&format=text"

# Get transcript in Spanish
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&lang=es"

# Get transcript without timestamps
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&timestamps=false"
```

**Response (JSON format):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "language": "en",
  "is_generated": false,
  "segments": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Never gonna give you up"
    },
    {
      "start": 3.5,
      "end": 6.0,
      "text": "Never gonna let you down"
    }
  ]
}
```

**Response (text format):**
```
Never gonna give you up Never gonna let you down...
```

#### Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "cache_enabled": true,
  "cache_dir": "./cache"
}
```

## Configuration

Configuration is managed through environment variables or the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server host binding |
| `PORT` | `8000` | Server port |
| `CACHE_DIR` | `./cache` | Cache directory path |
| `CACHE_ENABLED` | `true` | Enable/disable caching |
| `YTDLP_TIMEOUT` | `30` | yt-dlp timeout in seconds |
| `MAX_CONCURRENT_PROCESSES` | `2` | Max concurrent yt-dlp processes |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid YouTube URL or video ID |
| 404 | No subtitles found for the video |
| 408 | Request timeout (yt-dlp took too long) |
| 500 | Internal server error |

## Caching

The service caches transcripts in the filesystem to improve performance:

- Cache files are stored in `./cache/` by default
- Cache key format: `{video_id}_{lang}.json`
- Cache hits return results in < 10ms
- Cache can be disabled via `CACHE_ENABLED=false`

## Development

### Project Structure

```
yt-transcriber/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models.py            # Pydantic models
│   ├── api/
│   │   ├── __init__.py
│   │   └── transcript.py    # Transcript endpoint
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── vtt_parser.py    # WebVTT parser
│   └── services/
│       ├── __init__.py
│       ├── cache_manager.py # Caching layer
│       └── subtitle_extractor.py # yt-dlp wrapper
├── cache/                   # Cache directory (created automatically)
├── plans/                   # Implementation plans
├── specs/                   # PRD and specifications
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```

### Running Tests

Tests will be added in the `tests/` directory. To run tests:

```bash
pytest tests/ -v
```

## Docker Deployment (Optional)

A Dockerfile will be provided for containerized deployment.

## Security Notes

- The service binds to `127.0.0.1` by default (localhost only)
- URL sanitization prevents command injection
- No shell execution (`shell=False` in subprocess calls)
- Cache directory permissions should be restricted appropriately

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
