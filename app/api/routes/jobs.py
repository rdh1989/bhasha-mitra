from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory="app/ui/templates"
)

@router.get("/jobs")
async def jobs_page(request: Request):

    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request
        }
    )