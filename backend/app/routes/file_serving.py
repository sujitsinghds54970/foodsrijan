"""
File Serving Routes
Serves uploaded files (PDFs, images, etc.) from the uploads directory
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path

router = APIRouter()

# Get the uploads directory path - try multiple possible locations
BASE_DIR = Path(__file__).parent.parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# Also check for daily_entry_reports subdirectory
DAILY_ENTRY_REPORTS_DIR = UPLOADS_DIR / "daily_entry_reports"

@router.get("/files/{filename:path}")
async def serve_file(filename: str):
    """
    Serve a file from the uploads directory
    
    Args:
        filename: The name of the file to serve (can include subdirectory)
        
    Returns:
        FileResponse with the requested file
        
    Raises:
        HTTPException: If file not found or invalid filename
    """
    # Security: Prevent directory traversal attacks
    if ".." in filename or filename.startswith("/"):
        print(f"❌ [FILE_SERVING] Invalid filename attempted: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Try multiple possible file locations
    possible_paths = [
        UPLOADS_DIR / filename,  # Direct in uploads/
        DAILY_ENTRY_REPORTS_DIR / filename,  # In uploads/daily_entry_reports/
        BASE_DIR / filename,  # Relative to backend root
    ]
    
    file_path = None
    for path in possible_paths:
        print(f"🔍 [FILE_SERVING] Checking path: {path}")
        if path.exists() and path.is_file():
            file_path = path
            print(f"✅ [FILE_SERVING] File found at: {file_path}")
            break
    
    # Check if file exists
    if not file_path:
        print(f"❌ [FILE_SERVING] File not found: {filename}")
        print(f"   Searched in:")
        for path in possible_paths:
            print(f"   - {path}")
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    # Determine media type based on file extension
    media_type = "application/octet-stream"
    if filename.lower().endswith('.pdf'):
        media_type = "application/pdf"
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        media_type = f"image/{filename.split('.')[-1].lower()}"
    elif filename.lower().endswith('.txt'):
        media_type = "text/plain"
    
    print(f"📤 [FILE_SERVING] Serving file: {file_path} as {media_type}")
    
    # Return the file
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=os.path.basename(filename),
        headers={
            "Content-Disposition": f'inline; filename="{os.path.basename(filename)}"',
            "Cache-Control": "public, max-age=3600"
        }
    )
