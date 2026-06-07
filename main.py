import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import init_db
from app.utils import generate_all_assets
from app.routes import pages, api
import os

# 1. Startup initialization: Database & Assets seeder
init_db()
generate_all_assets()

# 2. Initialize FastAPI Application
app = FastAPI(
    title="SporoSentinel",
    description="Offline-First Fungal Contamination Intelligence Platform",
    version="1.0.0"
)

# Disable browser caching on dynamic HTML templates and enforce revalidation for static files/SW
@app.middleware("http")
async def add_cache_control_header(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/sw.js":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    elif path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    else:
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# 3. Mount Static Directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Mount Uploads Directory for scanned image history storage
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 5. Serve Service Worker from Root Scope (Crucial for PWA intercepts)
@app.get("/sw.js")
async def serve_service_worker():
    return FileResponse("sw.js", media_type="application/javascript")

# 6. Include Route Controllers
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")

if __name__ == "__main__":
    # Start ASGI Server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
