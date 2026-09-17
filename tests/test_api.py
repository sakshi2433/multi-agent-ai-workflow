import pytest
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_create_workflow(client):
    response = client.post(
        "/workflows",
        json={
            "request": "Search for the latest developments in artificial intelligence",
            "name": "AI Research Workflow",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["request"] == (
        "Search for the latest developments in artificial intelligence"
    )
    assert data["status"] == "completed"


def test_get_workflow(client):
    create_response = client.post(
        "/workflows",
        json={
            "request": "Test workflow retrieval",
            "name": "Test Workflow",
        },
    )

    assert create_response.status_code == 201

    workflow_id = create_response.json()["id"]

    response = client.get(f"/workflows/{workflow_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == workflow_id
    assert data["request"] == "Test workflow retrieval"


def test_get_workflow_trace(client):
    create_response = client.post(
        "/workflows",
        json={
            "request": "Test workflow trace",
            "name": "Trace Test",
        },
    )

    assert create_response.status_code == 201

    workflow_id = create_response.json()["id"]

    response = client.get(f"/workflows/{workflow_id}/trace")

    assert response.status_code == 200

    data = response.json()

    assert data["workflow_id"] == workflow_id
    assert "entries" in data
    assert len(data["entries"]) >= 1


def test_approve_workflow(client):
    create_response = client.post(
        "/workflows",
        json={
            "request": "Test workflow approval",
            "name": "Approval Test",
        },
    )

    assert create_response.status_code == 201

    workflow_id = create_response.json()["id"]

    response = client.post(f"/workflows/{workflow_id}/approve")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == workflow_id
    assert data["approval_status"] == "approved"


def test_reject_workflow(client):
    create_response = client.post(
        "/workflows",
        json={
            "request": "Test workflow rejection",
            "name": "Rejection Test",
        },
    )

    assert create_response.status_code == 201

    workflow_id = create_response.json()["id"]

    response = client.post(f"/workflows/{workflow_id}/reject")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == workflow_id
    assert data["status"] == "rejected"
    assert data["approval_status"] == "rejected"


def test_get_nonexistent_workflow(client):
    response = client.get(
        "/workflows/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404