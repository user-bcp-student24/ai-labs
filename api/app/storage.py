from __future__ import annotations

from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".md", ".pdf"}


async def store_requirement(file: UploadFile, upload_dir: Path) -> dict[str, str | int]:
    filename = file.filename or ""
    normalized_name = filename.replace("\\", "/")
    safe_name = PurePosixPath(normalized_name).name
    if (
        not safe_name
        or safe_name in {".", ".."}
        or safe_name != normalized_name
        or "\x00" in safe_name
        or Path(safe_name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS
    ):
        raise HTTPException(status_code=400, detail="Invalid file")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    target = upload_dir / safe_name
    target.write_bytes(content)
    return {"fileName": safe_name, "storedAt": str(target), "size": len(content)}