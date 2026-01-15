# YouTube Transcript Service

A self-hosted Python HTTP service using FastAPI and yt-dlp to fetch YouTube transcripts without third-party APIs.

## Features

- Fetch YouTube video transcripts by URL or video ID
- **AI-powered summarization** using GitHub Copilot CLI (short, medium, long)
- Support for multiple languages
- Automatic and manual subtitle support
- Response formats: JSON (with timestamps) or plain text
- Filesystem-based caching for transcripts and summaries
- Concurrency control to prevent resource exhaustion
- No video/audio downloads - subtitles only
- Cross-platform support (Windows & Linux)

## Requirements

- Python 3.11+
- yt-dlp (installed automatically with dependencies)
- **GitHub Copilot CLI** (optional, for summarization feature):
  ```bash
  npm install -g @github/copilot-cli
  ```

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
- `summary` (optional): Generate AI summary - `short`, `medium`, or `long`

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

# Get short AI summary (50-70 words)
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&summary=short"

# Get medium AI summary (250-350 words)
curl "http://localhost:8000/transcript?url=jfTPjyQlWsk&summary=medium"

# Get long AI summary as plain text (500-700 words)
curl "http://localhost:8000/transcript?url=jfTPjyQlWsk&summary=long&format=text"
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

**Summary Response (JSON format):**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "language": "en",
  "summary_length": "short",
  "summary": "The file contains full lyrics to Rick Astley's \"Never Gonna Give You Up,\" repeated in places (verses, chorus, and refrains). It lists lines of the song including verses about commitment, recognizing feelings, and the repeated chorus promising never to give up, let down, run around, desert, make cry, say goodbye, or lie and hurt you.",
  "is_generated": false
}
```

**Summary Response (text format):**
```
The file contains full lyrics to Rick Astley's "Never Gonna Give You Up," repeated in places...
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
| `COPILOT_CLI_PATH` | `copilot` | Path to Copilot CLI executable |
| `COPILOT_TIMEOUT` | `120` | Copilot CLI timeout in seconds |
| `COPILOT_MODEL` | `gpt-5-mini` | AI model for summarization |
| `MAX_CONCURRENT_COPILOT` | `1` | Max concurrent Copilot requests |
| `SUMMARY_CACHE_ENABLED` | `true` | Enable/disable summary caching |

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid YouTube URL or video ID |
| 404 | No subtitles found for the video |
| 408 | Request timeout (yt-dlp took too long) |
| 500 | Internal server error |
| 503 | Copilot CLI not available (summarization only) |

## Caching

The service caches both transcripts and summaries in the filesystem to improve performance:

**Transcript Caching:**
- Cache files are stored in `./cache/` by default
- Cache key format: `{video_id}_{lang}.json`
- Cache hits return results in < 10ms
- Can be disabled via `CACHE_ENABLED=false`

**Summary Caching:**
- Cache key format: `{video_id}_{lang}_summary_{length}.json`
- Each summary length (short/medium/long) is cached separately
- Prevents redundant AI requests and saves Copilot Premium usage
- Can be disabled via `SUMMARY_CACHE_ENABLED=false`

## AI Summarization

The service includes AI-powered summarization using GitHub Copilot CLI with the `gpt-5-mini` model.

### Summary Lengths

- **Short** (50-70 words): Quick overview of the video content
- **Medium** (250-350 words): Detailed summary with key points
- **Long** (500-700 words): Comprehensive analysis with context

### How It Works

1. Transcript is saved to a temporary file (to bypass Windows CLI length limits)
2. Copilot CLI is invoked with a prompt to read and summarize the file
3. Summary is cached to avoid redundant AI requests
4. Works cross-platform (Windows `.CMD` files, Linux direct execution)

### Example Use Cases

```bash
# Quick summary for social media
curl "http://localhost:8000/transcript?url=dQw4w9WgXcQ&summary=short&format=text"

# Detailed summary for blog post
curl "http://localhost:8000/transcript?url=jfTPjyQlWsk&summary=medium"

# Full analysis for documentation
curl "http://localhost:8000/transcript?url=jfTPjyQlWsk&summary=long&format=text"
```

### Notes

- Requires GitHub Copilot subscription (uses Premium requests)
- Summary generation takes 5-30 seconds depending on transcript length
- Very long videos (>90K chars) are fully supported
- UTF-8 encoding with error handling for special characters

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
│       ├── cache_manager.py      # Caching layer
│       ├── subtitle_extractor.py # yt-dlp wrapper
│       └── summarizer.py         # Copilot CLI wrapper
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
