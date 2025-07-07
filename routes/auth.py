from fastapi import APIRouter, Request, Form, HTTPException, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
import os
from typing import Optional
from loguru import logger

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Session management
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
SESSION_SERIALIZER = URLSafeTimedSerializer(SECRET_KEY)

# Get hashed password from environment
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_session_token(user_id: str = "admin") -> str:
    """Create a signed session token"""
    return SESSION_SERIALIZER.dumps({"user_id": user_id})

def verify_session_token(token: str) -> Optional[dict]:
    """Verify and decode a session token"""
    try:
        # Token expires after 24 hours (86400 seconds)
        return SESSION_SERIALIZER.loads(token, max_age=86400)
    except Exception as e:
        logger.debug(f"Invalid session token: {e}")
        return None

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Display the login page"""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error_message": error
        }
    )

@router.post("/login")
async def login(
    request: Request,
    password: str = Form(...)
):
    """Handle login form submission"""
    try:
        if not ADMIN_PASSWORD_HASH:
            logger.error("ADMIN_PASSWORD_HASH not configured")
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error_message": "Authentication not configured properly"
                }
            )

        # Verify password
        if not verify_password(password, ADMIN_PASSWORD_HASH):
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error_message": "Invalid password"
                }
            )

        # Create session token
        session_token = create_session_token()
        
        # Redirect to dashboard with session cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=86400,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        logger.info("User successfully logged in")
        return response

    except Exception as e:
        logger.error(f"Login error: {e}")
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error_message": "An error occurred during login"
            }
        )

def get_current_user(session_token: Optional[str] = Cookie(None)) -> Optional[dict]:
    """Dependency to get current authenticated user"""
    if not session_token:
        return None
    
    user_data = verify_session_token(session_token)
    return user_data

def require_auth(current_user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Dependency to require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user