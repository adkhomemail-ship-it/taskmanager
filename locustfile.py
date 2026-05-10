from __future__ import annotations

import random
import string
from datetime import date, timedelta

from locust import HttpUser, between, task


class TaskManagerUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.username = f"load{suffix}"
        self.password = "password123"
        response = self.client.post(
            "/api/auth/register",
            json={"username": self.username, "password": self.password},
            name="auth: register",
        )
        token = response.json().get("access_token") if response.ok else None
        if not token:
            response = self.client.post(
                "/api/auth/login",
                data={"username": self.username, "password": self.password},
                name="auth: login",
            )
            token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}
        self.task_ids: list[int] = []

    @task(4)
    def create_task(self):
        deadline = date.today() + timedelta(days=random.randint(1, 30))
        payload = {
            "title": f"Load task {random.randint(1, 1_000_000)}",
            "description": "Created by Locust load profile",
            "status": random.choice(["в ожидании", "в работе", "завершено"]),
            "priority": random.choice(["не важно", "важно", "критично"]),
            "deadline": deadline.isoformat(),
        }
        with self.client.post("/api/tasks/", json=payload, headers=self.headers, name="tasks: create", catch_response=True) as response:
            if response.status_code == 201:
                self.task_ids.append(response.json()["id"])
            else:
                response.failure(f"unexpected status {response.status_code}: {response.text}")

    @task(3)
    def list_tasks(self):
        self.client.get(
            f"/api/tasks/?sort_by={random.choice(['created_at', 'title', 'deadline', 'priority'])}",
            headers=self.headers,
            name="tasks: list",
        )

    @task(2)
    def update_task(self):
        if not self.task_ids:
            return
        task_id = random.choice(self.task_ids)
        payload = {
            "title": f"Updated load task {task_id}",
            "description": "Updated by Locust",
            "status": "в работе",
            "priority": "критично",
            "deadline": (date.today() + timedelta(days=7)).isoformat(),
        }
        self.client.put(f"/api/tasks/{task_id}", json=payload, headers=self.headers, name="tasks: update")

    @task(1)
    def delete_task(self):
        if not self.task_ids:
            return
        task_id = self.task_ids.pop(0)
        self.client.delete(f"/api/tasks/{task_id}", headers=self.headers, name="tasks: delete")
