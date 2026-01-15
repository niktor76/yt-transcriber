import asyncio
import logging
import shutil
from asyncio.subprocess import PIPE
from typing import Literal
from app.config import config

logger = logging.getLogger(__name__)


# Custom exceptions
class SummarizerError(Exception):
    """Base exception for summarization errors"""
    pass


class CopilotNotFoundError(SummarizerError):
    """Raised when GitHub Copilot CLI is not installed or not in PATH"""
    pass


class CopilotTimeoutError(SummarizerError):
    """Raised when Copilot CLI execution times out"""
    pass


class InvalidSummaryLengthError(SummarizerError):
    """Raised when an invalid summary length is provided"""
    pass


class SummarizationFailedError(SummarizerError):
    """Raised when summarization fails for any other reason"""
    pass


class Summarizer:
    """Service for generating summaries using GitHub Copilot CLI"""

    def __init__(self):
        """Initialize the summarizer with concurrency control"""
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_COPILOT)
        self._validate_copilot_installation()

    def _validate_copilot_installation(self):
        """Check if GitHub Copilot CLI is installed and available"""
        copilot_path = shutil.which(config.COPILOT_CLI_PATH)
        if not copilot_path:
            logger.warning(
                f"GitHub Copilot CLI not found at '{config.COPILOT_CLI_PATH}'. "
                "Summarization features will not work. "
                "Install with: npm install -g @github/copilot-cli"
            )
            # Don't raise exception here - let it fail gracefully when actually used
        else:
            logger.info(f"GitHub Copilot CLI found at: {copilot_path}")

    def _build_prompt(self, transcript_text: str, summary_length: Literal["short", "medium", "long"]) -> str:
        """
        Build prompt for Copilot CLI based on summary length.

        Args:
            transcript_text: The transcript text to summarize
            summary_length: Desired summary length

        Returns:
            Formatted prompt string
        """
        # Simple, direct prompts work best with Copilot CLI
        if summary_length == "short":
            prompt = f"Write a 50-70 word summary: {transcript_text}"
        elif summary_length == "medium":
            prompt = f"Write a 250-350 word summary with multiple paragraphs: {transcript_text}"
        elif summary_length == "long":
            prompt = f"Write a detailed 500-700 word summary with analysis: {transcript_text}"
        else:
            raise InvalidSummaryLengthError(f"Invalid summary length: {summary_length}")

        return prompt

    def _chunk_transcript(self, transcript_text: str, max_length: int) -> list[str]:
        """
        Split transcript into chunks if it exceeds max length.

        Args:
            transcript_text: The transcript text
            max_length: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(transcript_text) <= max_length:
            return [transcript_text]

        # Split by sentences (simple approach)
        sentences = transcript_text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence) + 2  # +2 for '. '
            if current_length + sentence_length > max_length and current_chunk:
                # Save current chunk and start new one
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add remaining chunk
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')

        logger.info(f"Split transcript into {len(chunks)} chunks")
        return chunks

    async def _execute_copilot(self, prompt: str, transcript_file: str = None) -> str:
        """
        Execute GitHub Copilot CLI with the given prompt.

        Args:
            prompt: The prompt to send to Copilot

        Returns:
            Copilot's response text

        Raises:
            CopilotNotFoundError: If Copilot CLI is not found
            CopilotTimeoutError: If execution times out
            SummarizationFailedError: If execution fails
        """
        # Check if Copilot is available and get full path
        import sys
        import os
        import subprocess
        import shlex

        copilot_path = shutil.which(config.COPILOT_CLI_PATH)

        # On Windows, try common npm global installation path if which() fails
        if not copilot_path and sys.platform == "win32":
            # Try APPDATA first
            appdata = os.getenv("APPDATA")
            if appdata:
                npm_path = os.path.join(appdata, "npm", "copilot.CMD")
                if os.path.exists(npm_path):
                    copilot_path = npm_path
                    logger.info(f"Found Copilot at npm global path: {copilot_path}")

            # Try USERPROFILE as fallback
            if not copilot_path:
                userprofile = os.getenv("USERPROFILE")
                if userprofile:
                    npm_path = os.path.join(userprofile, "AppData", "Roaming", "npm", "copilot.CMD")
                    if os.path.exists(npm_path):
                        copilot_path = npm_path
                        logger.info(f"Found Copilot at npm global path: {copilot_path}")

        if not copilot_path:
            raise CopilotNotFoundError(
                f"GitHub Copilot CLI not found at '{config.COPILOT_CLI_PATH}'. "
                "Install with: npm install -g @github/copilot-cli"
            )

        # Set environment variables including model selection
        env = os.environ.copy()
        if config.COPILOT_MODEL:
            env["GITHUB_COPILOT_MODEL"] = config.COPILOT_MODEL

        # Build command - Windows CMD files need to be run through cmd.exe
        if sys.platform == "win32" and copilot_path.lower().endswith('.cmd'):
            cmd = ["cmd.exe", "/c", copilot_path, "-p", prompt]
        else:
            cmd = [copilot_path, "-p", prompt]

        logger.info(f"Executing Copilot CLI with model: {config.COPILOT_MODEL}")
        logger.info(f"Command: {cmd}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        try:
            logger.info("Acquiring semaphore...")
            async with self._semaphore:
                logger.info("Semaphore acquired, running subprocess via executor...")

                # Use run_in_executor to avoid Windows asyncio subprocess issues
                loop = asyncio.get_event_loop()

                def run_subprocess():
                    """Run subprocess synchronously in executor"""
                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=config.COPILOT_TIMEOUT,
                            env=env,
                            text=True,
                            encoding='utf-8',
                            errors='replace'  # Replace invalid UTF-8 chars instead of failing
                        )
                        return result
                    except subprocess.TimeoutExpired as e:
                        raise CopilotTimeoutError(f"Summarization timed out after {config.COPILOT_TIMEOUT} seconds")

                # Run subprocess in thread pool executor
                result = await loop.run_in_executor(None, run_subprocess)

                stdout_text = result.stdout.strip() if result.stdout else ""
                stderr_text = result.stderr.strip() if result.stderr else ""

                logger.debug(f"Return code: {result.returncode}")
                logger.debug(f"Stdout length: {len(stdout_text)} characters")
                logger.debug(f"Stderr length: {len(stderr_text)} characters")

                if result.returncode != 0:
                    logger.error(f"Copilot CLI failed with return code {result.returncode}")
                    logger.error(f"Stderr: {stderr_text}")
                    raise SummarizationFailedError(f"Copilot CLI error (code {result.returncode}): {stderr_text}")

                # Copilot CLI outputs the actual response to stdout, but also outputs usage stats to stderr
                # We need to parse the response from stdout (the first line before the usage stats)
                if not stdout_text:
                    logger.error("Copilot CLI returned empty stdout")
                    logger.error(f"Stderr: {stderr_text}")
                    raise SummarizationFailedError("Copilot CLI returned empty response")

                # The actual summary is in stdout, everything before the blank lines
                response_lines = stdout_text.split('\n')
                # Filter out empty lines at the end and usage statistics
                summary_lines = []
                for line in response_lines:
                    if line.strip():
                        summary_lines.append(line)

                summary = '\n'.join(summary_lines)

                logger.info(f"Copilot response length: {len(summary)} characters")
                return summary

        except FileNotFoundError:
            raise CopilotNotFoundError(
                f"GitHub Copilot CLI not found at '{config.COPILOT_CLI_PATH}'"
            )

        except Exception as e:
            import traceback
            logger.error(f"Unexpected error during Copilot execution: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise SummarizationFailedError(f"Summarization failed: {str(e)}")

    async def summarize(
        self,
        transcript_text: str,
        summary_length: Literal["short", "medium", "long"]
    ) -> str:
        """
        Generate a summary of the transcript using GitHub Copilot CLI.

        Args:
            transcript_text: The full transcript text
            summary_length: Desired length ('short', 'medium', 'long')

        Returns:
            Generated summary text

        Raises:
            CopilotNotFoundError: If Copilot CLI is not installed
            CopilotTimeoutError: If summarization times out
            InvalidSummaryLengthError: If summary_length is invalid
            SummarizationFailedError: If summarization fails
        """
        logger.info(f"Starting summarization (length={summary_length}, transcript_size={len(transcript_text)})")

        # Save transcript to file to bypass Windows command-line length limits
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(transcript_text)
            transcript_file = os.path.abspath(f.name)

        try:
            # Build SHORT prompt that tells Copilot to read and summarize the file
            if summary_length == "short":
                prompt = f"Read the file '{transcript_file}' and write a 50-70 word summary of it."
            elif summary_length == "medium":
                prompt = f"Read the file '{transcript_file}' and write a 250-350 word summary of it."
            elif summary_length == "long":
                prompt = f"Read the file '{transcript_file}' and write a 500-700 word summary of it."

            final_summary = await self._execute_copilot(prompt, transcript_file)

            logger.info(f"Summarization complete (output_size={len(final_summary)})")
            return final_summary
        finally:
            # Clean up temp file
            if os.path.exists(transcript_file):
                os.unlink(transcript_file)



# Global summarizer instance
summarizer = Summarizer()
