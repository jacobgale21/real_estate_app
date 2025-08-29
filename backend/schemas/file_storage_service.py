import tempfile
from pydantic import BaseModel
from typing import List
import shutil
import os
class FileMetadata(BaseModel):
    filename: str
    file_path: str
    file_size: int

class FileStorageService:
    def __init__(self):
        self.input_files: List[FileMetadata] = []
        self.comparison_files: List[FileMetadata] = []
        self.temp_dir = tempfile.mkdtemp(prefix="real_estate_")
    
    def set_input(self, input: FileMetadata):
        self.input_files.append(input)

    def set_comparison(self, comparison: FileMetadata):
        self.comparison_files.append(comparison)

    def get_input_files(self):
        return self.input_files

    def get_comparison_files(self):
        return self.comparison_files

    def get_temp_dir(self):
        return self.temp_dir
    async def cleanup(self):
        try:
            for input_file in self.input_files:
                if os.path.exists(input_file.file_path):
                    os.remove(input_file.file_path)
            for comparison_file in self.comparison_files:
                if os.path.exists(comparison_file.file_path):
                    os.remove(comparison_file.file_path)
                    
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error in cleanup: {e}")