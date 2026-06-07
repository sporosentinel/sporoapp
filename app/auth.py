from fastapi import Request, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from app.database import get_db_connection, hash_password
from typing import Optional, Dict, Any

COOKIE_NAME = "sporo_session"

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to retrieve the logged-in user from the session cookie.
    """
    user_id = request.cookies.get(COOKIE_NAME)
    if not user_id:
        return None
    try:
        user = get_user_by_id(int(user_id))
        return user
    except (ValueError, TypeError):
        return None

def login_required(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """
    Ensures the user is logged in, redirecting to the login screen if not.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: Dict[str, Any] = Depends(login_required)):
        if user["role"] not in self.allowed_roles:
            # Redirect to their default dashboard based on role
            redirect_url = "/admin" if user["role"] == "admin" else "/farmer"
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": redirect_url}
            )
        return user
