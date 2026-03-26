from fastapi import FastAPI, Request

from app.database import lifespan
from app.routers.auth import pages_router as auth_pages_router
from app.routers.auth import router as auth_router
from app.routers.tasks import pages_router as tasks_pages_router
from app.routers.tasks import router as tasks_router


app = FastAPI(title="Task Manager", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(auth_pages_router)
app.include_router(tasks_pages_router)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.middleware("http")
async def attach_bearer_token_from_cookie(request: Request, call_next):
    cookie_token = request.cookies.get("access_token")
    if cookie_token and "authorization" not in request.headers:
        request.scope["headers"].append((b"authorization", cookie_token.encode()))
    return await call_next(request)
