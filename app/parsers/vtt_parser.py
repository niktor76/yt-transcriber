import re
from typing import List
from app.models import TranscriptSegment


def parse_vtt(content: str) -> List[TranscriptSegment]:
    """
    Parse WebVTT subtitle format into transcript segments.

    Args:
        content: Raw VTT file content

    Returns:
        List of TranscriptSegment objects

    Raises:
        ValueError: If VTT content is malformed
    """
    segments = []

    # Remove VTT header
    lines = content.strip().split('\n')

    # Skip WEBVTT header and initial blank lines
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('WEBVTT'):
            start_idx = i + 1
            break

    # Parse cues
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and cue identifiers
        if not line or line.isdigit():
            i += 1
            continue

        # Check if this is a timestamp line
        timestamp_pattern = r'(\d{2}:)?(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}:)?(\d{2}):(\d{2})\.(\d{3})'
        match = re.match(timestamp_pattern, line)

        if match:
            # Parse start time
            start_h = int(match.group(1)[:-1]) if match.group(1) else 0
            start_m = int(match.group(2))
            start_s = int(match.group(3))
            start_ms = int(match.group(4))
            start_time = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000

            # Parse end time
            end_h = int(match.group(5)[:-1]) if match.group(5) else 0
            end_m = int(match.group(6))
            end_s = int(match.group(7))
            end_ms = int(match.group(8))
            end_time = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000

            # Collect text lines until next timestamp or empty line
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(timestamp_pattern, lines[i].strip()):
                text_line = lines[i].strip()
                # Remove VTT tags like <c> or <v>
                # Use possessive quantifier to prevent ReDoS attacks
                text_line = re.sub(r'<[^>]*?>', '', text_line)
                if text_line:
                    text_lines.append(text_line)
                i += 1

            if text_lines:
                text = ' '.join(text_lines)
                segments.append(TranscriptSegment(
                    start=start_time,
                    end=end_time,
                    text=text
                ))
        else:
            i += 1

    if not segments:
        raise ValueError("No valid segments found in VTT content")

    return segments


def segments_to_plain_text(segments: List[TranscriptSegment]) -> str:
    """
    Convert transcript segments to plain text (no timestamps).

    Args:
        segments: List of transcript segments

    Returns:
        Plain text transcript
    """
    return ' '.join(segment.text for segment in segments)
