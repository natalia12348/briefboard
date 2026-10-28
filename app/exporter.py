import csv
import io

from .models import Board

FIELDS = ["id", "title", "column", "owner", "due", "priority", "kind", "points", "moscow", "score", "labels"]


def to_csv(board: Board) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(FIELDS)
    for card in board.cards:
        writer.writerow(
            [
                card.id,
                card.title,
                card.column,
                card.owner or "",
                card.due or "",
                card.priority,
                card.kind,
                card.points,
                card.moscow,
                card.score,
                ";".join(card.labels),
            ]
        )
    return buffer.getvalue()


def to_markdown(board: Board) -> str:
    lines = [f"# Delivery board ({board.method.title()})", ""]
    for column in board.columns:
        in_col = [c for c in board.cards if c.column == column.id]
        limit = f" (WIP {len(in_col)}/{column.wip})" if column.wip else ""
        lines.append(f"## {column.title}{limit}")
        lines.append("")
        if not in_col:
            lines.append("_Nothing here._")
        for card in in_col:
            box = "x" if column.id == "done" else " "
            meta = [card.priority, f"{card.points} pts", card.moscow]
            if card.owner:
                meta.insert(0, card.owner)
            if card.due:
                meta.append(f"due {card.due}")
            lines.append(f"- [{box}] **{card.id}** {card.title} ({', '.join(meta)})")
        lines.append("")
    for heading, items in (
        ("Decisions", board.decisions),
        ("Risks", board.risks),
        ("Open questions", board.questions),
    ):
        if items:
            lines.append(f"## {heading}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
    return "\n".join(lines)


def to_json(board: Board) -> str:
    return board.model_dump_json(indent=2)


RENDERERS = {
    "csv": (to_csv, "text/csv"),
    "markdown": (to_markdown, "text/markdown"),
    "json": (to_json, "application/json"),
}
