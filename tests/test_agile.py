from datetime import date

from app import agile, extractor
from app.models import Board
from app.sample import SAMPLES

REF = date(2026, 10, 28)


def build(method="kanban", velocity=20):
    data = extractor.extract(SAMPLES["en"], REF)
    board = Board(columns=agile.columns_for(method), cards=data["cards"])
    return agile.apply_method(board, method, velocity)


def test_columns_per_method():
    assert [c.title for c in agile.columns_for("scrum")][1] == "Sprint Backlog"
    assert agile.columns_for("kanban")[2].wip == 3


def test_scrum_respects_velocity_for_optional_work():
    board = build("scrum", velocity=30)
    committed = sum(c.points for c in board.cards if c.column in ("todo", "doing", "review", "done"))
    assert committed <= 30
    assert any(c.column == "backlog" for c in board.cards)


def test_scrum_prefers_must_have():
    board = build("scrum", velocity=14)
    planned = [c for c in board.cards if c.column == "todo"]
    assert any(c.moscow == "Must" for c in planned)
    backlog = [c for c in board.cards if c.column == "backlog"]
    assert all(c.moscow != "Must" for c in backlog)


def test_scrum_warns_when_musts_exceed_velocity():
    board = build("scrum", velocity=5)
    result = agile.metrics(board, REF)
    assert result["committed"] > 5
    assert any("exceeds velocity" in s for s in result["suggestions"])


def test_metrics_flags_wip_breach():
    board = build("kanban")
    for card in board.cards[:5]:
        card.column = "doing"
    result = agile.metrics(board, REF)
    doing = next(c for c in result["columns"] if c["id"] == "doing")
    assert doing["over"]
    assert any("WIP limit" in s for s in result["suggestions"])


def test_metrics_overdue_and_completion():
    board = build("kanban")
    result = agile.metrics(board, date(2026, 12, 1))
    assert result["overdue"] > 0
    assert 0 < result["completion"] < 100
