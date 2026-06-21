from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(
    directory="app/ui/templates"
)

@router.get("/settings")
async def settings(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="/pages/settings.html",
        context={}
    )