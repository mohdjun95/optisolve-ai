from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routes import landing, app_page, api

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="OptiSolve AI", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Share templates with route modules
landing.templates = templates
app_page.templates = templates

app.include_router(landing.router)
app.include_router(app_page.router)
app.include_router(api.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
