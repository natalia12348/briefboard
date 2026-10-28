from collections import Counter
from datetime import date

from .cards import MOSCOW_RANK, parse_date
from .models import Board, Column

PRESETS = {
    "kanban": [
        ("backlog", "Backlog", None),
        ("todo", "To Do", None),
        ("doing", "In Progress", 3),
        ("review", "Review", 2),
        ("done", "Done", None),
    ],
    "scrum": [
        ("backlog", "Product Backlog", None),
        ("todo", "Sprint Backlog", None),
        ("doing", "In Progress", None),
        ("review", "Review", None),
        ("done", "Done", None),
    ],
    "scrumban": [
        ("backlog", "Backlog", None),
        ("todo", "Ready", 5),
        ("doing", "In Progress", 3),
        ("review", "Review", 2),
        ("done", "Done", None),
    ],
}


def columns_for(method: str) -> list[Column]:
    return [Column(id=i, title=t, wip=w) for i, t, w in PRESETS[method]]


def plan_sprint(board: Board) -> None:
    in_flight = sum(c.points for c in board.cards if c.column in ("doing", "review", "done"))
    committed = in_flight
    candidates = [c for c in board.cards if c.column in ("backlog", "todo")]
    candidates.sort(key=lambda c: (MOSCOW_RANK.get(c.moscow, 1), -c.score))
    for card in candidates:
        if card.moscow == "Won't":
            card.column = "backlog"
        elif card.moscow == "Must" or committed + card.points <= board.velocity:
            card.column = "todo"
            committed += card.points
        else:
            card.column = "backlog"


def order_cards(board: Board) -> None:
    index = {col.id: i for i, col in enumerate(board.columns)}
    board.cards.sort(
        key=lambda c: (
            index.get(c.column, 0),
            MOSCOW_RANK.get(c.moscow, 1),
            -c.score,
        )
    )


def apply_method(board: Board, method: str, velocity: int) -> Board:
    board.method = method
    board.velocity = velocity
    board.columns = columns_for(method)
    valid = {c.id for c in board.columns}
    for card in board.cards:
        if card.column not in valid:
            card.column = "backlog"
    if method == "scrum":
        plan_sprint(board)
    order_cards(board)
    return board


def metrics(board: Board, today: date) -> dict:
    cards = board.cards
    total_points = sum(c.points for c in cards)
    done_points = sum(c.points for c in cards if c.column == "done")

    columns = []
    for col in board.columns:
        in_col = [c for c in cards if c.column == col.id]
        columns.append(
            {
                "id": col.id,
                "title": col.title,
                "count": len(in_col),
                "points": sum(c.points for c in in_col),
                "wip": col.wip,
                "over": bool(col.wip and len(in_col) > col.wip),
            }
        )

    owners: dict[str, dict] = {}
    for c in cards:
        if c.column == "done":
            continue
        key = c.owner or "Unassigned"
        slot = owners.setdefault(key, {"owner": key, "cards": 0, "points": 0})
        slot["cards"] += 1
        slot["points"] += c.points
    owner_load = sorted(owners.values(), key=lambda o: -o["points"])

    overdue = [
        c
        for c in cards
        if c.column != "done" and (d := parse_date(c.due)) is not None and d < today
    ]
    blocked = [c for c in cards if "blocked" in c.labels and c.column != "done"]
    unassigned = [c for c in cards if not c.owner and c.column != "done"]

    result = {
        "total": len(cards),
        "points": total_points,
        "done_points": done_points,
        "completion": round(100 * done_points / total_points) if total_points else 0,
        "columns": columns,
        "owners": owner_load,
        "overdue": len(overdue),
        "blocked": len(blocked),
        "unassigned": len(unassigned),
        "moscow": dict(Counter(c.moscow for c in cards)),
        "priority": dict(Counter(c.priority for c in cards)),
        "kinds": dict(Counter(c.kind for c in cards)),
        "committed": sum(c.points for c in cards if c.column in ("todo", "doing", "review", "done")),
        "velocity": board.velocity,
    }
    result["suggestions"] = suggestions(board, result, overdue, blocked, unassigned)
    return result


def suggestions(board: Board, m: dict, overdue, blocked, unassigned) -> list[str]:
    out: list[str] = []
    for col in m["columns"]:
        if col["over"]:
            out.append(
                f"{col['title']} is over its WIP limit ({col['count']}/{col['wip']}). "
                "Finish work in flight before pulling anything new."
            )
    if overdue:
        names = ", ".join(c.id for c in overdue[:4])
        out.append(f"{len(overdue)} open card(s) are past their due date ({names}). Re-plan or escalate.")
    if blocked:
        names = ", ".join(c.id for c in blocked[:4])
        out.append(f"{len(blocked)} card(s) are blocked ({names}). Agree who clears each blocker today.")
    if unassigned:
        out.append(f"{len(unassigned)} open card(s) have no owner. Ownership is a precondition for flow.")
    large = [c for c in board.cards if c.points >= 13 and c.column != "done"]
    if large:
        out.append(f"{large[0].id} is estimated at {large[0].points} points. Split it into slices of 5 or less.")
    open_points = sum(o["points"] for o in m["owners"])
    if len(m["owners"]) > 1 and open_points:
        top = m["owners"][0]
        share = round(100 * top["points"] / open_points)
        if share >= 50 and top["owner"] != "Unassigned":
            out.append(f"{top['owner']} carries {share}% of open points. Rebalance to protect throughput.")
    if board.method == "scrum":
        if m["committed"] > board.velocity:
            out.append(
                f"Sprint commitment ({m['committed']} pts) exceeds velocity ({board.velocity} pts)."
            )
        else:
            out.append(
                f"Sprint commitment is {m['committed']} of {board.velocity} pts. "
                "Keep the remainder as buffer for unplanned work."
            )
    musts = [c for c in board.cards if c.moscow == "Must" and c.column == "backlog"]
    if musts:
        out.append(f"{len(musts)} Must-have card(s) sit in the backlog. Pull them into the next cycle.")
    if not out:
        out.append("Flow looks healthy: no WIP breaches, blockers or overdue work.")
    return out
