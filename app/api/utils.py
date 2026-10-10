"""Small helpers shared by routers."""
from fastapi import UploadFile

from app.config import settings
from app.exceptions import ValidationError


def read_upload(file: UploadFile, allowed_extensions: tuple[str, ...]) -> bytes:
    """Read an uploaded file, enforcing extension and size limits."""
    name = (file.filename or "").lower()
    if not name.endswith(allowed_extensions):
        raise ValidationError(f"Only {', '.join(allowed_extensions)} files are accepted.")
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise ValidationError(f"File is too large (max {settings.max_upload_mb} MB).")
    return data
