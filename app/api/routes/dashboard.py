from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory="app/ui/templates"
)

@router.get("/")
async def dashboard(request: Request):

    stats = {
        "videos_processed": 1245,
        "translation_hours": 842.5,
        "completed_jobs": 318,
        "active_jobs": 3
    }

    return templates.TemplateResponse(
        "/pages/dashboard.html",
        {
            "request": request,
            "stats": stats
        }
    )