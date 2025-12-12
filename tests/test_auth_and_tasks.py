import pytest


@pytest.mark.asyncio
async def test_register_login_and_task_flow(client):
    # register admin
    r = await client.post(
        "/auth/register",
        json={"email": "admin@x.com", "password": "Admin@1234", "role": "ADMIN", "full_name": "Admin"},
    )
    assert r.status_code == 200, r.text

    # login
    r = await client.post("/auth/token", data={"username": "admin@x.com", "password": "Admin@1234"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create another user
    r = await client.post(
        "/auth/register",
        json={"email": "u1@x.com", "password": "User@1234", "role": "MEMBER"},
    )
    assert r.status_code == 200, r.text
    user_id = r.json()["id"]

    # create task with assignee + tag
    r = await client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Task A",
            "description": "desc",
            "status": "TODO",
            "priority": "HIGH",
            "users": [{"user_id": user_id, "role": "ASSIGNEE"}],
            "tags": ["backend", "urgent"],
        },
    )
    assert r.status_code == 200, r.text
    task = r.json()
    assert task["title"] == "Task A"
    assert user_id in task["assignees"]
    assert "backend" in task["tags"]

    # update task
    r = await client.patch(f"/tasks/{task['id']}", headers=headers, json={"status": "IN_PROGRESS"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "IN_PROGRESS"

    # bulk update
    r = await client.patch(
        "/tasks/bulk",
        headers=headers,
        json={"updates": [{"id": task["id"], "patch": {"priority": "CRITICAL"}}]},
    )
    assert r.status_code == 200, r.text
    assert task["id"] in r.json()["updated_ids"]

    # filter
    r = await client.post(
        "/tasks/filter",
        headers=headers,
        json={"logic": "AND", "priority_in": ["CRITICAL"], "page": 1, "page_size": 10},
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1

    # timeline
    r = await client.get("/timeline?days=7", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
