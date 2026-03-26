from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, get_password_hash
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate
from app.templates import templates


router = APIRouter(prefix="/api/auth", tags=["auth"])
pages_router = APIRouter(tags=["pages"])


@pages_router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "login_error": None, "register_error": None},
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь уже существует")

    user = User(username=user_data.username, hashed_password=get_password_hash(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@pages_router.post("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        token = register(UserCreate(username=username, password=password), db)
    except HTTPException as exc:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "login_error": None, "register_error": exc.detail},
            status_code=exc.status_code,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "login_error": None, "register_error": exc.errors()[0]["msg"]},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    response = RedirectResponse(url="/me", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", f"Bearer {token.access_token}", httponly=True, samesite="lax")
    return response


@pages_router.post("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "login_error": "Неверный логин или пароль", "register_error": None},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    access_token = create_access_token({"sub": user.username})
    response = RedirectResponse(url="/me", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("access_token", f"Bearer {access_token}", httponly=True, samesite="lax")
    return response


@pages_router.post("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
