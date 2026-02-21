from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from ..config import AVAILABLE_MODELS, GOOGLE_API_KEY

router = APIRouter()
templates: Jinja2Templates = None  # set by main.py


@router.get("/app")
async def solver_page(request: Request):
    return templates.TemplateResponse("app.html", {
        "request": request,
        "models": AVAILABLE_MODELS,
        "has_server_key": bool(GOOGLE_API_KEY),
    })
