from fastapi.testclient import TestClient

from app.main import app
from app.sample import SAMPLES

client = TestClient(app)


def analyze(method="kanban"):
    return client.post(
        "/api/analyze",
        json={"notes": SAMPLES["en"], "method": method, "reference_date": "2026-10-28", "use_llm": False},
    )


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_analyze_returns_board_and_metrics():
    data = analyze().json()
    assert len(data["board"]["cards"]) == 9
    assert data["metrics"]["total"] == 9
    assert data["engine"] == "rules"


def test_analyze_rejects_empty_result():
    response = client.post("/api/analyze", json={"notes": "Nothing actionable here."})
    assert response.status_code == 422


def test_method_switch_relabels_columns():
    board = analyze().json()["board"]
    response = client.post("/api/method", json={"board": board, "method": "scrum", "velocity": 15})
    assert response.status_code == 200
    titles = [c["title"] for c in response.json()["board"]["columns"]]
    assert titles[1] == "Sprint Backlog"


def test_refresh_rescoring():
    board = analyze().json()["board"]
    board["cards"][0]["priority"] = "low"
    board["cards"][0]["points"] = 13
    refreshed = client.post("/api/refresh", json=board).json()
    card = next(c for c in refreshed["board"]["cards"] if c["id"] == board["cards"][0]["id"])
    assert card["moscow"] in ("Could", "Must")
    assert card["score"] < 2


def test_exports():
    board = analyze().json()["board"]
    csv_text = client.post("/api/export", json={"board": board, "format": "csv"}).text
    assert csv_text.splitlines()[0].startswith("id,title")
    md = client.post("/api/export", json={"board": board, "format": "markdown"}).text
    assert "## Done" in md and "## Decisions" in md
    raw = client.post("/api/export", json={"board": board, "format": "json"}).json()
    assert len(raw["cards"]) == 9


def test_playbook_and_samples():
    assert len(client.get("/api/playbook").json()) >= 6
    assert "Action items" in client.get("/api/sample?lang=en").json()["notes"]


def test_frontend_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Briefboard" in response.text
