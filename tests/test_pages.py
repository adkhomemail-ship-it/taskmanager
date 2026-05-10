from starlette.requests import Request

from app.models import TaskPriority, TaskStatus, User
from app.routers.tasks import create_task_page
from tests.conftest import auth_headers, register_user


def _login_cookie(client, username="alice", password="password123"):
    token = register_user(client, username, password)
    client.cookies.set("access_token", f"Bearer {token}")
    return token


def _create_api_task(client, headers, title, description="", priority="важно", status="в ожидании", deadline="2026-03-30"):
    response = client.post(
        "/api/tasks/",
        json={
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "deadline": deadline,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_landing_page_renders_forms(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Task Manager" in response.text
    assert "Регистрация" in response.text
    assert "Вход" in response.text


def test_register_page_success_sets_cookie_and_redirects(client):
    response = client.post("/register", data={"username": "alice", "password": "password123"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/me"
    assert "access_token" in response.headers["set-cookie"]


def test_register_page_duplicate_and_validation_errors(client):
    client.post("/register", data={"username": "alice", "password": "password123"}, follow_redirects=False)
    duplicate = client.post("/register", data={"username": "alice", "password": "password123"})
    assert duplicate.status_code == 400
    assert "Пользователь уже существует" in duplicate.text

    validation = client.post("/register", data={"username": "алиса", "password": "password123"})
    assert validation.status_code == 400
    assert "Логин должен содержать" in validation.text


def test_login_page_success_error_and_logout(client):
    register_user(client, "alice", "password123")

    bad_login = client.post("/login", data={"username": "alice", "password": "bad"})
    assert bad_login.status_code == 401
    assert "Неверный логин или пароль" in bad_login.text

    good_login = client.post("/login", data={"username": "alice", "password": "password123"}, follow_redirects=False)
    assert good_login.status_code == 303
    assert good_login.headers["location"] == "/me"
    assert "access_token" in good_login.headers["set-cookie"]

    logout = client.post("/logout", follow_redirects=False)
    assert logout.status_code == 303
    assert logout.headers["location"] == "/"
    assert "access_token" in logout.headers["set-cookie"]


def test_me_page_requires_auth_and_renders_user_tasks(client):
    assert client.get("/me").status_code == 401
    token = _login_cookie(client, "alice")
    task = _create_api_task(client, auth_headers(token), "Visible task", "Shown on page")

    response = client.get("/me?sort_by=title")
    assert response.status_code == 200
    assert "Мои задачи" in response.text
    assert "alice" in response.text
    assert "Visible task" in response.text
    assert "Shown on page" in response.text
    assert str(task["title"]) in response.text


def test_create_update_delete_task_from_page(client):
    _login_cookie(client, "alice")

    create_response = client.post(
        "/me/tasks",
        data={
            "title": "Page task",
            "description": "Created from form",
            "status_value": "в ожидании",
            "priority_value": "важно",
            "deadline": "2026-04-01",
        },
        follow_redirects=False,
    )
    assert create_response.status_code == 303
    task = client.get("/api/tasks/").json()[0]
    assert task["title"] == "Page task"

    update_response = client.post(
        f"/me/tasks/{task['id']}/update",
        data={
            "title": "Updated page task",
            "description": "Updated from form",
            "status_value": "завершено",
            "priority_value": "критично",
            "deadline": "2026-04-02",
        },
        follow_redirects=False,
    )
    assert update_response.status_code == 303
    updated_task = client.get(f"/api/tasks/{task['id']}").json()
    assert updated_task["title"] == "Updated page task"
    assert updated_task["status"] == "завершено"

    delete_response = client.post(f"/me/tasks/{task['id']}/delete", follow_redirects=False)
    assert delete_response.status_code == 303
    assert client.get("/api/tasks/").json() == []


def test_page_form_error_branches(client, db_session):
    _login_cookie(client, "alice")

    create_error = client.post(
        "/me/tasks",
        data={"title": "", "description": "", "status_value": "в ожидании", "priority_value": "важно"},
    )
    assert create_error.status_code == 400

    user = db_session.query(User).filter(User.username == "alice").first()
    request = Request({"type": "http", "method": "POST", "path": "/me/tasks", "headers": []})
    direct_error = create_task_page(
        request=request,
        title="",
        description="",
        status_value=TaskStatus.pending,
        priority_value=TaskPriority.low,
        deadline=None,
        current_user=user,
        db=db_session,
    )
    assert direct_error.status_code == 400

    update_error = client.post("/me/tasks/999/update", data={"title": "Missing", "description": "", "status_value": "в ожидании", "priority_value": "важно", "deadline": "2026-01-01",
    },
)
    assert update_error.status_code == 400
    assert "Задача не найдена" in update_error.text


def test_backlog_page_filters_search_paginates_and_handles_empty(client):
    token = _login_cookie(client, "alice")
    headers = auth_headers(token)
    for index in range(6):
        priority = "критично" if index % 2 == 0 else "важно"
        _create_api_task(
            client,
            headers,
            f"Release task {index}",
            "release",
            priority=priority,
            deadline=f"2026-01-{index + 1:02d}",
        )
    _create_api_task(client, headers, "No deadline", "notes", priority="критично", deadline=None)

    response = client.get("/backlog?backlog_view=important&search_query=release&search_in=description&per_page=5&page=5")
    assert response.status_code == 200
    assert "Бэклог" in response.text
    assert "Показаны задачи" in response.text
    assert "Release task" in response.text
    assert "Всего задач: 6" in response.text
    
    fallback = client.get("/backlog?per_page=7")
    assert fallback.status_code == 200
    assert "Всего задач: 7" in fallback.text

    # New authenticated user has an empty backlog.
    client.cookies.clear()
    _login_cookie(client, "bob")
    empty = client.get("/backlog")
    assert empty.status_code == 200
    assert "В бэклоге пока нет задач" in empty.text


def test_backlog_validation_errors(client):
    _login_cookie(client, "alice")
    assert client.get("/backlog?backlog_view=bad").status_code == 422
    assert client.get("/backlog?search_in=bad").status_code == 422
    assert client.get("/backlog?page=0").status_code == 422
