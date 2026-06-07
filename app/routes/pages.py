from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.auth import get_current_user, login_required, RoleChecker, COOKIE_NAME, get_user_by_username
from app.database import get_db_connection, hash_password
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    if user["role"] == "admin":
        return RedirectResponse(url="/admin")
    return RedirectResponse(url="/farmer")

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request=request, name="login.html", context={"current_user": None})

@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user_by_username(username)
    if not user or user["password_hash"] != hash_password(password):
        return templates.TemplateResponse(request=request, name="login.html", context={
            "error": "Invalid username or password.",
            "current_user": None
        })
    
    # Successful login, set cookie session
    response = RedirectResponse(url="/onboarding" if not user["region"] else "/", status_code=303)
    response.set_cookie(key=COOKIE_NAME, value=str(user["id"]), max_age=86400 * 30, path="/")
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return response

@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_get(request: Request, user=Depends(login_required)):
    return templates.TemplateResponse(request=request, name="onboarding.html", context={"current_user": user})

@router.get("/admin", response_class=HTMLResponse)
async def admin_get(request: Request, user=Depends(RoleChecker(allowed_roles=["admin"]))):
    return templates.TemplateResponse(request=request, name="admin.html", context={"current_user": user})

@router.get("/farmer", response_class=HTMLResponse)
async def farmer_get(request: Request, user=Depends(RoleChecker(allowed_roles=["farmer"]))):
    # Retrieve scan history from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM scans WHERE user_id = ? ORDER BY id DESC", 
        (user["id"],)
    )
    scans = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return templates.TemplateResponse(request=request, name="farmer.html", context={
        "current_user": user,
        "history": scans
    })
