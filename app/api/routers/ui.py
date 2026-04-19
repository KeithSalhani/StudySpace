from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import get_services
from app.services.frontend import FRONTEND_ENTRY_JS, get_frontend_asset_version

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    services = get_services(request)
    return services.templates.TemplateResponse(
        request,
        "index.html",
        {
            "frontend_built": FRONTEND_ENTRY_JS.exists(),
            "frontend_asset_version": get_frontend_asset_version(),
        },
    )
