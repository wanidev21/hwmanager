from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/pages", StaticFiles(directory="frontend/pages"), name="pages")


@app.get("/firebase-config.js")
async def firebase_config():
    return FileResponse("frontend/firebase-config.js", media_type="application/javascript")


@app.get("/manifest.json")
async def manifest():
    return FileResponse("frontend/manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        "frontend/sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


@app.get("/login")
async def login():
    return FileResponse("frontend/login.html")


@app.get("/api/health")
async def health():
    return {"success": True}
