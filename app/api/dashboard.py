from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory="app/ui/templates"
)

@router.get("/")
async def dashboard(request: Request):

    stats = {
        "videos": 124,
        "hours": 540,
        "completed": 118,
        "active": 3
    }

    return templates.TemplateResponse(
        request=request,
        name="/pages/dashboard.html",
        context={
            "stats": stats
        }
    )