from fastapi import Request, Depends
from schemas.file_storage_service import FileStorageService

def get_file_storage_service(request: Request) -> FileStorageService:
    """Get file storage service from app state"""
    return request.app.state.file_storage_service