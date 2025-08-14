from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from .auth import get_current_user

# Journey state is no longer stored locally; provide a placeholder via Supabase or return None

router = APIRouter(
	prefix="",  # Empty prefix
	tags=["ui"],
	responses={404: {"description": "Not found"}},
)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


@router.get("/checkin/{check_in_id}", response_class=HTMLResponse)
async def checkin_page(request: Request, check_in_id: int, current_user: dict = Depends(get_current_user)):
	"""Serve the check-in page for a specific check-in"""
	if not current_user:
		return RedirectResponse(url="/auth/login", status_code=302)
	return templates.TemplateResponse("checkin.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def checkin_dashboard_page(request: Request, current_user: dict = Depends(get_current_user)):
	"""Serve the checkin dashboard page"""
	if not current_user:
		return RedirectResponse(url="/auth/login", status_code=302)
	return templates.TemplateResponse("checkin_dashboard.html", {"request": request})

@router.get("/all-checkins")
async def all_checkins_page(current_user: dict = Depends(get_current_user)):
	"""All Check-ins page"""
	if not current_user:
		return RedirectResponse(url="/login", status_code=302)
	
	return templates.TemplateResponse("all_checkins.html", {"request": {}})



