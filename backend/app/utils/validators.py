"""Input validation and sanitization utilities."""

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

MAX_FILENAME_LENGTH = 255

class ValidationError(HTTPException):
    """Custom validation error."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


def validate_file_size(file_size: int, max_size_mb: int | None = None) -> None:
    """Validate file size is within limits.

    Args:
        file_size: File size in bytes
        max_size_mb: Maximum size in MB (defaults to settings.MAX_FILE_SIZE_MB)

    Raises:
        ValidationError: If file size exceeds limit
    """
    max_size = (max_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024
    if file_size > max_size:
        msg = (
            f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds "
            f"maximum allowed size ({max_size / 1024 / 1024}MB)"
        )
        raise ValidationError(msg)


def validate_file_extension(
    filename: str, allowed_extensions: list[str] | None = None
) -> str:
    """Validate file extension is allowed.

    Args:
        filename: Original filename
        allowed_extensions: List of allowed extensions (defaults to
            settings.ALLOWED_EXTENSIONS)

    Returns:
        Lowercase file extension

    Raises:
        ValidationError: If extension is not allowed
    """
    allowed = allowed_extensions or settings.ALLOWED_EXTENSIONS
    ext = filename.split(".")[-1].lower() if "." in filename else ""

    if not ext:
        msg = "File must have an extension"
        raise ValidationError(msg)

    if ext not in allowed:
        msg = f"File type '.{ext}' not allowed. Allowed types: {', '.join(allowed)}"
        raise ValidationError(msg)

    return ext


def validate_mime_type(file: UploadFile, extension: str) -> None:
    """Validate MIME type matches file extension.

    Args:
        file: Uploaded file
        extension: File extension

    Raises:
        ValidationError: If MIME type doesn't match extension
    """
    if not file.content_type:
        return  # Skip if no content type provided

    # Common MIME type mappings
    mime_mappings = {
        "pdf": ["application/pdf"],
        "docx": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        "doc": ["application/msword"],
        "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
        "xls": ["application/vnd.ms-excel"],
        "pptx": [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ],
        "ppt": ["application/vnd.ms-powerpoint"],
        "txt": ["text/plain"],
        "md": ["text/markdown", "text/plain"],
        "html": ["text/html"],
        "png": ["image/png"],
        "jpg": ["image/jpeg"],
        "jpeg": ["image/jpeg"],
        "tiff": ["image/tiff"],
    }

    expected_mimes = mime_mappings.get(extension, [])
    if expected_mimes and file.content_type not in expected_mimes:
        msg = f"MIME type '{file.content_type}' doesn't match extension '.{extension}'"
        raise ValidationError(msg)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = Path(filename).name

    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")

    return filename


def sanitize_query(query: str, max_length: int = 1000) -> str:
    """Sanitize search/chat query.

    Args:
        query: User query
        max_length: Maximum query length

    Returns:
        Sanitized query

    Raises:
        ValidationError: If query is invalid
    """
    # Strip whitespace
    query = query.strip()

    # Check if empty
    if not query:
        msg = "Query cannot be empty"
        raise ValidationError(msg)

    # Check length
    if len(query) > max_length:
        msg = f"Query too long (max {max_length} characters)"
        raise ValidationError(msg)

    # Remove null bytes
    return query.replace("\x00", "")


def validate_upload_file(file: UploadFile) -> tuple[str, str]:
    """Validate uploaded file comprehensively.

    Args:
        file: Uploaded file

    Returns:
        Tuple of (sanitized_filename, extension)

    Raises:
        ValidationError: If file is invalid
    """
    if not file.filename:
        msg = "No filename provided"
        raise ValidationError(msg)

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)

    # Validate extension
    extension = validate_file_extension(safe_filename)

    # Validate MIME type
    validate_mime_type(file, extension)

    return safe_filename, extension
