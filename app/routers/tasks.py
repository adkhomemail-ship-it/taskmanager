from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from sqlalchemy import case, or_
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Task, TaskPriority, TaskStatus, User
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.templates import templates


router = APIRouter(prefix="/api/tasks", tags=["tasks"])
pages_router = APIRouter(tags=["pages"])

SORT_OPTIONS = {
    "title": "По заголовку",
    "created_at": "По дате создания",
    "deadline": "По дате дедлайна",
    "priority": "По приоритету",
}

BACKLOG_VIEW_OPTIONS = {
    "all": "Все задачи",
    "important": "Ближайшие важные",
}

PER_PAGE_OPTIONS = [5, 10, 20, 50]

SEARCH_IN_OPTIONS = {
    "title": "В названии",
    "description": "В описании",
    "all": "Везде",
}


def build_tasks_query(db: Session, user_id: int, sort_by: str):
    query = db.query(Task).filter(Task.owner_id == user_id)

    if sort_by == "title":
        return query.order_by(Task.title.asc(), Task.created_at.desc())
    if sort_by == "deadline":
        return query.order_by(Task.deadline.is_(None), Task.deadline.asc(), Task.created_at.desc())
    if sort_by == "priority":
        priority_order = case(
            (Task.priority == TaskPriority.high, 0),
            (Task.priority == TaskPriority.medium, 1),
            (Task.priority == TaskPriority.low, 2),
            else_=3,
        )
        return query.order_by(priority_order, Task.created_at.desc())
    return query.order_by(Task.created_at.desc())


def build_page_context(request: Request, current_user: User, tasks: list[Task], sort_by: str, error: str | None = None):
    return {
        "request": request,
        "user": current_user,
        "tasks": tasks,
        "statuses": list(TaskStatus),
        "priorities": list(TaskPriority),
        "sort_options": SORT_OPTIONS,
        "sort_by": sort_by,
        "error": error,
    }


def apply_search(query, search_query: str, search_in: str):
    if not search_query:
        return query

    pattern = f"%{search_query}%"
    if search_in == "title":
        return query.filter(Task.title.ilike(pattern))
    if search_in == "description":
        return query.filter(Task.description.ilike(pattern))
    return query.filter(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))


def build_backlog_query(db: Session, user_id: int, sort_by: str, backlog_view: str, search_query: str, search_in: str):
    if backlog_view == "important":
        priority_order = case(
            (Task.priority == TaskPriority.high, 0),
            (Task.priority == TaskPriority.medium, 1),
            (Task.priority == TaskPriority.low, 2),
            else_=3,
        )
        query = (
            db.query(Task)
            .filter(Task.owner_id == user_id, Task.deadline.is_not(None))
            .order_by(priority_order, Task.deadline.asc(), Task.created_at.asc())
        )
        return apply_search(query, search_query, search_in)
    return apply_search(build_tasks_query(db, user_id, sort_by), search_query, search_in)


def get_user_task_or_404(task_id: int, user_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == user_id).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@router.get("/", response_model=list[TaskRead])
def list_tasks(
    sort_by: str = Query("created_at", pattern="^(title|created_at|deadline|priority)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_tasks_query(db, current_user.id, sort_by).all()


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = Task(**task_data.model_dump(), owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_task_or_404(task_id, current_user.id, db)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = get_user_task_or_404(task_id, current_user.id, db)
    for field, value in task_data.model_dump().items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = get_user_task_or_404(task_id, current_user.id, db)
    db.delete(task)
    db.commit()


@pages_router.get("/me", response_class=HTMLResponse)
def me(
    request: Request,
    sort_by: str = Query("created_at", pattern="^(title|created_at|deadline|priority)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = build_tasks_query(db, current_user.id, sort_by).all()
    return templates.TemplateResponse("me.html", build_page_context(request, current_user, tasks, sort_by))


@pages_router.get("/backlog", response_class=HTMLResponse)
def backlog(
    request: Request,
    sort_by: str = Query("created_at", pattern="^(title|created_at|deadline|priority)$"),
    backlog_view: str = Query("all", pattern="^(all|important)$"),
    search_query: str = Query(""),
    search_in: str = Query("all", pattern="^(title|description|all)$"),
    per_page: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if per_page not in PER_PAGE_OPTIONS:
        per_page = 10

    query = build_backlog_query(db, current_user.id, sort_by, backlog_view, search_query.strip(), search_in)
    total_tasks = query.count()
    total_pages = max(1, (total_tasks + per_page - 1) // per_page)
    current_page = min(page, total_pages)
    tasks = query.offset((current_page - 1) * per_page).limit(per_page).all()
    context = build_page_context(request, current_user, tasks, sort_by)
    context["backlog_view"] = backlog_view
    context["backlog_view_options"] = BACKLOG_VIEW_OPTIONS
    context["per_page"] = per_page
    context["per_page_options"] = PER_PAGE_OPTIONS
    context["page"] = current_page
    context["total_pages"] = total_pages
    context["total_tasks"] = total_tasks
    context["search_query"] = search_query
    context["search_in"] = search_in
    context["search_in_options"] = SEARCH_IN_OPTIONS
    return templates.TemplateResponse("backlog.html", context)


@pages_router.post("/me/tasks", response_class=HTMLResponse)
def create_task_page(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status_value: TaskStatus = Form(TaskStatus.pending),
    priority_value: TaskPriority = Form(TaskPriority.low),
    deadline: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        create_task(
            TaskCreate(title=title, description=description, status=status_value, priority=priority_value, deadline=deadline),
            current_user,
            db,
        )
    except (HTTPException, ValidationError) as exc:
        tasks = build_tasks_query(db, current_user.id, "created_at").all()
        return templates.TemplateResponse(
            "me.html",
            build_page_context(
                request,
                current_user,
                tasks,
                "created_at",
                exc.detail if isinstance(exc, HTTPException) else exc.errors()[0]["msg"],
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/me", status_code=status.HTTP_303_SEE_OTHER)


@pages_router.post("/me/tasks/{task_id}/update", response_class=HTMLResponse)
def update_task_page(
    request: Request,
    task_id: int,
    title: str = Form(...),
    description: str = Form(""),
    status_value: TaskStatus = Form(...),
    priority_value: TaskPriority = Form(...),
    deadline: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        update_task(
            task_id,
            TaskUpdate(title=title, description=description, status=status_value, priority=priority_value, deadline=deadline),
            current_user,
            db,
        )
    except (HTTPException, ValidationError) as exc:
        tasks = build_tasks_query(db, current_user.id, "created_at").all()
        error = exc.detail if isinstance(exc, HTTPException) else exc.errors()[0]["msg"]
        return templates.TemplateResponse(
            "me.html",
            build_page_context(request, current_user, tasks, "created_at", error),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(url="/me", status_code=status.HTTP_303_SEE_OTHER)


@pages_router.post("/me/tasks/{task_id}/delete")
def delete_task_page(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_task(task_id, current_user, db)
    return RedirectResponse(url="/me", status_code=status.HTTP_303_SEE_OTHER)
