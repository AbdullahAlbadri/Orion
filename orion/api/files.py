"""Shared file handling for customer and team routes: upload checks and safe download responses."""

import re
from typing import Optional

from fastapi import HTTPException, Response, UploadFile, status

from orion.api.context import ApiContext
from orion.tools.files import ALLOWED, MAX_BYTES, MAX_FILES_PER_ORDER, sniff_type


async def read_upload(c: ApiContext, upload: UploadFile) -> tuple[str, str, bytes]:
    """Checks every customer upload goes through: size, and a type taken from the bytes. Returns (name, type, data)."""
    if c.files is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "file storage not available")
    data = await upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "file is larger than 10 MB")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "empty file")
    content_type = sniff_type(data)
    if content_type is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "use PNG, JPG, WEBP, SVG, PDF, AI or EPS")
    return re.sub(r"[\x00-\x1f/\\]", "_", upload.filename or "file")[:200], content_type, data


async def store_upload(c: ApiContext, order_id: str, customer_id: str, upload: UploadFile) -> dict:
    if c.files is not None and await c.accounts.count_files(order_id) >= MAX_FILES_PER_ORDER:
        raise HTTPException(status.HTTP_409_CONFLICT, f"at most {MAX_FILES_PER_ORDER} files per order")
    name, content_type, data = await read_upload(c, upload)
    key = c.files.save(data, ALLOWED[content_type])
    row = await c.accounts.add_file(order_id, customer_id, name, content_type, len(data), key)
    return {"file_id": str(row["id"]), "name": row["name"], "content_type": row["content_type"], "size": row["size"]}


async def file_response(c: ApiContext, order_id: str, file_id: str) -> Response:
    return serve_file(c, await c.accounts.order_file(order_id, file_id))


def serve_file(c: ApiContext, row: Optional[dict]) -> Response:
    """A stored file (row with name, content_type, storage_key) as a download that can never run as a page."""
    if row is None or c.files is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
    safe_name = re.sub(r'[^\w.\- ]', "_", row["name"])
    return Response(
        content=c.files.load(row["storage_key"]),
        media_type=row["content_type"],
        headers={
            # Never run anything from an uploaded file (SVG can contain script)
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


def file_ids_in(answers: dict) -> set[str]:
    """Every file id referenced in a form reply."""
    ids = set()
    for value in answers.values():
        if isinstance(value, list):
            ids |= {str(v["file_id"]) for v in value if isinstance(v, dict) and "file_id" in v}
    return ids
