from tests.conftest import auth_headers, register_user


def _create_task(client, headers, **overrides):
    payload = {
        "title": "Prepare release",
        "description": "Check changelog",
        "status": "в ожидании",
        "priority": "важно",
        "deadline": "2026-03-30",
    }
    payload.update(overrides)
    response = client.post("/api/tasks/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_task_crud_flow(client, authorized_headers):
    created = _create_task(client, authorized_headers)
    assert created["id"] > 0
    assert created["title"] == "Prepare release"
    assert created["status"] == "в ожидании"
    assert created["priority"] == "важно"
    assert created["deadline"] == "2026-03-30"

    list_response = client.get("/api/tasks/", headers=authorized_headers)
    assert list_response.status_code == 200
    assert [task["id"] for task in list_response.json()] == [created["id"]]

    get_response = client.get(f"/api/tasks/{created['id']}", headers=authorized_headers)
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Prepare release"

    update_payload = {
        "title": "Send release",
        "description": "Build final artifact",
        "status": "в работе",
        "priority": "критично",
        "deadline": "2026-03-29",
    }
    update_response = client.put(f"/api/tasks/{created['id']}", json=update_payload, headers=authorized_headers)
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Send release"
    assert update_response.json()["status"] == "в работе"

    delete_response = client.delete(f"/api/tasks/{created['id']}", headers=authorized_headers)
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    missing_response = client.get(f"/api/tasks/{created['id']}", headers=authorized_headers)
    assert missing_response.status_code == 404


def test_task_ownership_is_enforced(client):
    alice_token = register_user(client, "alice")
    bob_token = register_user(client, "bob")
    alice_headers = auth_headers(alice_token)
    bob_headers = auth_headers(bob_token)

    task = _create_task(client, alice_headers, title="Alice private task")

    assert client.get(f"/api/tasks/{task['id']}", headers=bob_headers).status_code == 404
    assert client.put(f"/api/tasks/{task['id']}", json={
        "title": "Hacked",
        "description": "",
        "status": "завершено",
        "priority": "не важно",
        "deadline": None,
    }, headers=bob_headers).status_code == 404
    assert client.delete(f"/api/tasks/{task['id']}", headers=bob_headers).status_code == 404

    bob_list = client.get("/api/tasks/", headers=bob_headers).json()
    assert bob_list == []
    alice_list = client.get("/api/tasks/", headers=alice_headers).json()
    assert [item["title"] for item in alice_list] == ["Alice private task"]


def test_list_tasks_sorting_modes(client, authorized_headers):
    _create_task(client, authorized_headers, title="Bravo", priority="не важно", deadline=None)
    _create_task(client, authorized_headers, title="Alpha", priority="критично", deadline="2026-01-02")
    _create_task(client, authorized_headers, title="Charlie", priority="важно", deadline="2026-01-01")

    by_title = client.get("/api/tasks/?sort_by=title", headers=authorized_headers).json()
    assert [task["title"] for task in by_title] == ["Alpha", "Bravo", "Charlie"]

    by_deadline = client.get("/api/tasks/?sort_by=deadline", headers=authorized_headers).json()
    assert [task["title"] for task in by_deadline] == ["Charlie", "Alpha", "Bravo"]

    by_priority = client.get("/api/tasks/?sort_by=priority", headers=authorized_headers).json()
    assert [task["title"] for task in by_priority] == ["Alpha", "Charlie", "Bravo"]


def test_task_validation_errors(client, authorized_headers):
    invalid_title = client.post("/api/tasks/", json={"title": "", "description": ""}, headers=authorized_headers)
    assert invalid_title.status_code == 422

    invalid_priority = client.post(
        "/api/tasks/",
        json={"title": "Task", "description": "", "status": "в ожидании", "priority": "urgent", "deadline": None},
        headers=authorized_headers,
    )
    assert invalid_priority.status_code == 422

    invalid_sort = client.get("/api/tasks/?sort_by=unknown", headers=authorized_headers)
    assert invalid_sort.status_code == 422


def test_create_task_defaults(client, authorized_headers):
    response = client.post("/api/tasks/", json={"title": "Only title"}, headers=authorized_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["description"] == ""
    assert body["status"] == "в ожидании"
    assert body["priority"] == "не важно"
    assert body["deadline"] is None
