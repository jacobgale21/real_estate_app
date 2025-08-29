from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from middleware import verify_token
from core.dependencies import get_file_storage_service
from schemas.file_storage_service import FileStorageService, FileMetadata
import uuid
import shutil
import os
from typing import List
from pdf_handle import extract_property_type, extract_property_info

# API Endpoints
app = APIRouter()

@app.post("/upload-input-pdf")
async def upload_input_pdf(file: UploadFile = File(...), token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Upload the main MLS report PDF"""
    try:

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Generate unique file ID
        file_id = f"input_{uuid.uuid4().hex[:8]}"
        
        # Save file to temporary directory
        file_path = os.path.join(file_storage_service.temp_dir, f"{file_id}.pdf")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Store file info
        file_metadata = FileMetadata(
            filename=file_id,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
        )
        file_storage_service.set_input(file_metadata)
        
        return {
            "success": True,
            "message": "Input PDF uploaded successfully",
            "file_id": file_id,
            "filename": file.filename,
            "file_size": file_metadata.file_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/upload-comparison-pdf")
async def upload_comparison_pdf(files: List[UploadFile] = File(...), token: str = Depends(verify_token), file_storage_service: FileStorageService = Depends(get_file_storage_service)):
    """Upload comparison property PDFs"""
    try:
        uploaded_file_info = []
        for file in files:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            
            # Generate unique file ID
            file_id = f"comp_{uuid.uuid4().hex[:8]}"
            
            # Save file to temporary directory
            file_path = os.path.join(file_storage_service.temp_dir, f"{file_id}.pdf")
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_metadata = FileMetadata(
                filename=file_id,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
            )
            file_storage_service.set_comparison(file_metadata)
            uploaded_file_info.append({
                "file_id": file_id,
                "filename": file.filename,
                "file_size": file_metadata.file_size,
            })
            temp_property_type = extract_property_type(file_storage_service.input_files[0].file_path)
            current_property_type = extract_property_type(file_storage_service.comparison_files[0].file_path)
            print(temp_property_type, current_property_type)
            if temp_property_type != current_property_type:
                try:
                    print("Type mismatch")
                    # Call comparison function to auto fill the data
                    # Think of best way to optimize this as the information is already extracted from the file, save locally it does not have to be run again
                    property_info, price_info, features_info, is_rental = extract_property_info(file_storage_service.input_files[0].file_path)
                    
                    extracted_data = {}
                    
                    if property_info and len(property_info) > 0:
                        for key, value in property_info[0].items():
                            key = key.replace(" ", "")
                            key  = key.lower()
                            if value is not None:
                                extracted_data[key] = value
                    if features_info and len(features_info) > 0:
                        for key, value in features_info[0].items():
                            key = key.replace(" ", "")
                            key  = key.lower()
                            if value is not None:
                                extracted_data[key] = value
                    return {
                        "success": True,
                        "type_mismatch": True,
                        "message": "Type mismatch, auto filled data",
                        "uploaded_files": uploaded_file_info,
                        "extracted_data": extracted_data   
                    }
                except Exception as e:
                    print(f"Error in type mismatch: {e}")
            
        return {
            "success": True,
            "type_mismatch": False,
            "message": f"{len(uploaded_file_info)} comparison PDF(s) uploaded successfully",
            "uploaded_files": uploaded_file_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
__all__ = ["app"]