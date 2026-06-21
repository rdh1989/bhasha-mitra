from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory="app/ui/templates"
)

@router.get("/settings")
async def settings_page(request: Request):

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request
        }
    )