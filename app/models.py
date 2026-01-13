from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """A single transcript segment with timing information"""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcript text for this segment")


class TranscriptResponse(BaseModel):
    """Response model for transcript endpoint"""
    video_id: str = Field(..., description="YouTube video ID")
    language: str = Field(..., description="Language code of the transcript")
    is_generated: bool = Field(..., description="Whether subtitles are auto-generated")
    segments: List[TranscriptSegment] = Field(..., description="List of transcript segments")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class TranscriptRequest(BaseModel):
    """Request parameters for transcript endpoint"""
    url: str = Field(..., description="YouTube URL or video ID")
    lang: str = Field("en", description="Language code")
    format: Literal["json", "text"] = Field("json", description="Response format")
    timestamps: bool = Field(True, description="Include timestamps in response")
