from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates: Jinja2Templates = None  # set by main.py


@router.get("/")
async def landing_page(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})
