"""File download endpoint for SKPL Agent.

Provides a secure file download API at /api/file/download.
Files are served from the workspace directory with path traversal protection.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/file", tags=["file"])


# Safe workspace root — all file downloads must be within this directory
# _file.py is at app/_router/_file.py (one level deeper than _app.py)
# Need 5 dirname levels to reach backend/ directory
_WORKSPACE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "data",
    "workspaces",
)


@router.get("/download")
async def download_file(
    path: str = Query(..., description="Absolute path to the file to download"),
    filename: Optional[str] = Query(None, description="Override download filename")
):
    """Download a file from the workspace.

    The file path is validated to ensure it is within the workspace root
    directory to prevent path traversal attacks.

    Args:
        path: Absolute path to the file.
        filename: Optional override for the download filename.

    Returns:
        FileResponse with the requested file.
    """
    file_path = Path(path).resolve()

    # Resolve workspace root
    workspace_root = Path(_WORKSPACE_ROOT).resolve()

    # Ensure the file is within the workspace root
    try:
        file_path.relative_to(workspace_root)
    except ValueError:
        # Also allow files in the temp directory
        temp_root = Path(os.path.join(
            os.path.dirname(workspace_root), "temp"
        )).resolve()
        try:
            file_path.relative_to(temp_root)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: file is not within the allowed workspace directory",
            )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")

    download_name = filename or file_path.name

    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/octet-stream",
    )
