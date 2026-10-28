import re
from datetime import date
from typing import Optional

from .models import Card

FIB = [1, 2, 3, 5, 8, 13]
VALUE = {"critical": 13, "high": 8, "medium": 5, "low": 2}
MOSCOW_RANK = {"Must": 0, "Should": 1, "Could": 2, "Won't": 3}

CRITICAL = re.compile(
    r"\b(blocker|critical|outage|p0|sev1|krytyczn\w*|awari\w*|blokuj\w*)\b", re.I
)
HIGH = re.compile(
    r"\b(urgent|asap|important|high priority|top priority|p1|pilne|pilny|pilna|"
    r"ważne|ważny|priorytet\w*|natychmiast\w*)\b",
    re.I,
)
LOW = re.compile(
    r"\b(nice to have|optional|someday|low priority|p3|when possible|opcjonalnie|"
    r"kiedyś|niski priorytet|bez pośpiechu)\b",
    re.I,
)
PARKED = re.compile(
    r"\b(postpone\w*|parked|park it|not now|defer\w*|odłożon\w*|nie teraz|zawieszon\w*)\b",
    re.I,
)
BUG = re.compile(
    r"\b(bug|bugs|fix|hotfix|defect|crash\w*|regression|błąd|błędy|błędu|napraw\w*)\b",
    re.I,
)
SPIKE = re.compile(
    r"\b(research|investigate|investigation|spike|explore|poc|prototype|feasibility|"
    r"zbadaj|zbadać|zbada\w*|przeanalizuj\w*|analiz\w*|rozeznanie)\b",
    re.I,
)
FEATURE = re.compile(
    r"\b(implement\w*|build|create|add|introduce|launch|ship|feature|zaimplementuj\w*|"
    r"wdroż\w*|dodaj|dodać|stwórz|stworzyć|zbuduj\w*|wprowadź\w*)\b",
    re.I,
)
SMALL = re.compile(
    r"\b(quick|small|minor|tiny|simple|drobn\w*|szybk\w*|prost\w*)\b", re.I
)
LARGE = re.compile(
    r"\b(large|big|complex|major|migration|migrate|refactor\w*|overhaul|rewrite|"
    r"duż\w*|złożon\w*|migracj\w*|zmigruj\w*|refaktor\w*|przebudow\w*)\b",
    re.I,
)
DONE = re.compile(
    r"\b(done|completed|finished|shipped|released|zrobione|zrobiony|zrobiona|gotowe|"
    r"gotowy|ukończon\w*|zakończon\w*|wdrożon\w*|skończon\w*|skonczon\w*|"
    r"ukonczon\w*|zakonczon\w*|wdrozon\w*)\b",
    re.I,
)
NOT_YET_DONE = re.compile(r"\b(?:to be|needs? to be|when|until|once|before|po)\s+done\b", re.I)
REVIEW = re.compile(
    r"\b(in review|under review|awaiting review|pr open|w recenzji|do recenzji|"
    r"do przeglądu|w review)\b",
    re.I,
)
DOING = re.compile(
    r"\b(in progress|working on|started|ongoing|wip|doing|w trakcie|w toku|w progresie|"
    r"w progress|pracuje|pracuję|pracują|robi|robię|robią|realizuje|rozpoczęt\w*|"
    r"rozpoczet\w*|trwa)\b",
    re.I,
)
BLOCKED = re.compile(
    r"\b(blocked|waiting for|waiting on|zablokowan\w*|czeka na|oczekuje na)\b", re.I
)
STATUS_TAIL = re.compile(
    r"\s*[-–—,(]?\s*\b(in review|under review|awaiting review|in progress|working on it|"
    r"done|completed|finished|blocked|w recenzji|w trakcie|w toku|zrobione|gotowe)\b\)?\s*[.!]?\s*$",
    re.I,
)
POINTS = re.compile(
    r"(?:,\s*)?\b(\d{1,2})\s?(?:sp|pts?|points?|punkt\w*)\b|(?:,\s*)?\bsp\s?[:=]\s?(\d{1,2})\b",
    re.I,
)
HASHTAG = re.compile(r"(?:^|\s)#([^\W\d_][\w-]{1,24})")

LABEL_KEYWORDS = {
    "frontend": ("frontend", "ui", "css", "react", "landing"),
    "backend": ("backend", "api", "database", "server", "baza danych"),
    "design": ("design", "ux", "mockup", "makiet"),
    "data": ("data", "report", "dashboard", "raport", "analytics", "warehouse"),
    "security": ("security", "gdpr", "rodo", "bezpiecze"),
    "infra": ("deploy", "ci/cd", "infra", "hosting", "staging", "wdroż"),
    "client": ("client", "customer", "klient"),
    "budget": ("budget", "budżet", "cost", "koszt", "finance"),
    "legal": ("legal", "contract", "terms", "umow", "prawn"),
}


def snap(n: int) -> int:
    return min(FIB, key=lambda f: abs(f - n))


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def infer_priority(text: str, due: Optional[date], ref: date) -> str:
    if CRITICAL.search(text):
        return "critical"
    if LOW.search(text):
        return "low"
    if HIGH.search(text):
        return "high"
    if due is not None and (due - ref).days <= 2:
        return "high"
    return "medium"


def infer_kind(text: str) -> str:
    if BUG.search(text):
        return "bug"
    if SPIKE.search(text):
        return "spike"
    if FEATURE.search(text):
        return "feature"
    return "task"


def infer_labels(text: str) -> list[str]:
    lowered = text.lower()
    found = [
        label
        for label, words in LABEL_KEYWORDS.items()
        if any(re.search(rf"\b{re.escape(w)}", lowered) for w in words)
    ]
    return found[:3]


def estimate_points(text: str, kind: str, explicit: Optional[int] = None) -> int:
    if explicit:
        return snap(explicit)
    if LARGE.search(text):
        base = 8
    elif SMALL.search(text):
        base = 1
    else:
        words = len(text.split())
        base = 2 if words <= 5 else 3 if words <= 10 else 5 if words <= 16 else 8
    if kind == "spike":
        base = min(base, 3)
    if kind == "bug":
        base = min(base, 5)
    return base


def infer_column(text: str, checked: bool, assigned: bool) -> str:
    cleaned = NOT_YET_DONE.sub("", text)
    if checked or DONE.search(cleaned):
        return "done"
    if REVIEW.search(text):
        return "review"
    if DOING.search(text):
        return "doing"
    return "todo" if assigned else "backlog"


def urgency(due: Optional[date], ref: date) -> int:
    if due is None:
        return 0
    days = (due - ref).days
    if days <= 0:
        return 8
    if days <= 2:
        return 6
    if days <= 7:
        return 3
    return 1


def moscow_for(priority: str, due: Optional[date], text: str) -> str:
    if PARKED.search(text):
        return "Won't"
    if priority == "critical":
        return "Must"
    if priority == "high":
        return "Must" if due is not None else "Should"
    if priority == "medium":
        return "Should"
    return "Could"


def score_for(priority: str, kind: str, due: Optional[date], points: int, ref: date) -> float:
    value = VALUE[priority] + urgency(due, ref) + (3 if kind == "bug" else 0)
    return round(value / max(points, 1), 2)


def rescore(card: Card, ref: date) -> Card:
    due = parse_date(card.due)
    card.score = score_for(card.priority, card.kind, due, card.points, ref)
    card.moscow = moscow_for(card.priority, due, f"{card.title} {card.source}")
    return card


def make_card(
    index: int,
    title: str,
    owner: Optional[str],
    due: Optional[date],
    column: str,
    ref: date,
    source: str = "",
    priority: Optional[str] = None,
    kind: Optional[str] = None,
    points: Optional[int] = None,
    labels: Optional[list[str]] = None,
) -> Card:
    context = f"{title} {source}"
    priority = priority or infer_priority(context, due, ref)
    kind = kind or infer_kind(context)
    merged = list(labels or [])
    for label in infer_labels(context):
        if label not in merged:
            merged.append(label)
    if BLOCKED.search(context) and "blocked" not in merged:
        merged.insert(0, "blocked")
    card = Card(
        id=f"BB-{index:02d}",
        title=title,
        owner=owner,
        due=due.isoformat() if due else None,
        priority=priority,
        kind=kind,
        points=estimate_points(context, kind, points),
        column=column,
        labels=merged[:5],
        source=source,
    )
    return rescore(card, ref)
