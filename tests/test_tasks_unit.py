from datetime import date

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import get_password_hash
from app.models import Task, TaskPriority, TaskStatus, User
from app.routers.tasks import apply_search, build_backlog_query, build_page_context, build_tasks_query, get_user_task_or_404


def _user(db_session, username="alice"):
    user = User(username=username, hashed_password=get_password_hash("password123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _task(db_session, user, title, description="", priority=TaskPriority.low, status=TaskStatus.pending, deadline=None):
    task = Task(
        title=title,
        description=description,
        priority=priority,
        status=status,
        deadline=deadline,
        owner_id=user.id,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_build_tasks_query_sorts_by_title_deadline_priority_and_default(db_session):
    user = _user(db_session)
    _task(db_session, user, "Bravo", priority=TaskPriority.low, deadline=None)
    _task(db_session, user, "Alpha", priority=TaskPriority.high, deadline=date(2026, 1, 2))
    _task(db_session, user, "Charlie", priority=TaskPriority.medium, deadline=date(2026, 1, 1))

    assert [task.title for task in build_tasks_query(db_session, user.id, "title").all()] == ["Alpha", "Bravo", "Charlie"]
    assert [task.title for task in build_tasks_query(db_session, user.id, "deadline").all()] == ["Charlie", "Alpha", "Bravo"]
    assert [task.title for task in build_tasks_query(db_session, user.id, "priority").all()] == ["Alpha", "Charlie", "Bravo"]
    assert len(build_tasks_query(db_session, user.id, "created_at").all()) == 3


def test_build_tasks_query_filters_by_owner(db_session):
    alice = _user(db_session, "alice")
    bob = _user(db_session, "bob")
    _task(db_session, alice, "Alice task")
    _task(db_session, bob, "Bob task")

    assert [task.title for task in build_tasks_query(db_session, alice.id, "title").all()] == ["Alice task"]


def test_apply_search_filters_title_description_and_all(db_session):
    user = _user(db_session)
    _task(db_session, user, "Buy milk", description="grocery list")
    _task(db_session, user, "Write report", description="milk metrics")
    base = db_session.query(Task).filter(Task.owner_id == user.id)

    assert [task.title for task in apply_search(base, "Buy", "title").all()] == ["Buy milk"]
    assert [task.title for task in apply_search(base, "metrics", "description").all()] == ["Write report"]
    assert {task.title for task in apply_search(base, "milk", "all").all()} == {"Buy milk", "Write report"}
    assert apply_search(base, "", "all").count() == 2


def test_build_backlog_query_important_only_deadline_tasks_and_search(db_session):
    user = _user(db_session)
    _task(db_session, user, "High soon", priority=TaskPriority.high, deadline=date(2026, 1, 2))
    _task(db_session, user, "Medium first", priority=TaskPriority.medium, deadline=date(2026, 1, 1))
    _task(db_session, user, "No deadline", priority=TaskPriority.high, deadline=None)

    important_titles = [task.title for task in build_backlog_query(db_session, user.id, "title", "important", "", "all").all()]
    assert important_titles == ["High soon", "Medium first"]

    all_titles = [task.title for task in build_backlog_query(db_session, user.id, "title", "all", "Medium", "title").all()]
    assert all_titles == ["Medium first"]


def test_get_user_task_or_404_returns_owned_task_and_rejects_missing(db_session):
    user = _user(db_session)
    task = _task(db_session, user, "Owned")

    assert get_user_task_or_404(task.id, user.id, db_session).title == "Owned"
    with pytest.raises(HTTPException) as exc_info:
        get_user_task_or_404(task.id + 999, user.id, db_session)
    assert exc_info.value.status_code == 404


def test_build_page_context_contains_template_options(db_session):
    user = _user(db_session)
    task = _task(db_session, user, "Owned")
    scope = {"type": "http", "method": "GET", "path": "/me", "headers": []}
    request = Request(scope)

    context = build_page_context(request, user, [task], "title", "Ошибка")
    assert context["request"] is request
    assert context["user"] is user
    assert context["tasks"] == [task]
    assert context["sort_by"] == "title"
    assert context["error"] == "Ошибка"
    assert TaskStatus.pending in context["statuses"]
    assert TaskPriority.high in context["priorities"]
