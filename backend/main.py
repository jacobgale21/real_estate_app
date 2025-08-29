import uvicorn
from fastapi import FastAPI
from schemas.file_storage_service import FileStorageService
from contextlib import asynccontextmanager
from api import files, reports
from fastapi.middleware.cors import CORSMiddleware
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup events go here
    print("Application startup: Initializing resources...")
    app.state.file_storage_service = FileStorageService()
    # Example: Connect to a database, load configuration, etc.
    yield
    # Shutdown events go here
    print("Application shutdown: Cleaning up resources...")
    if hasattr(app.state, 'file_storage_service'):
        await app.state.file_storage_service.cleanup()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register your routers with prefixes and tags
app.include_router(files.app)
app.include_router(reports.app)


# Optional: Add a root endpoint
@app.get("/")
async def root():
    return {"message": "Real Estate API is running!", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    