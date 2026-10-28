import re
from datetime import date, timedelta
from typing import Optional

from .cards import (
    HASHTAG,
    POINTS,
    STATUS_TAIL,
    infer_column,
    make_card,
)
from .models import Card

WEEKDAYS = {
    "monday": 0, "mon": 0, "poniedziałek": 0, "poniedziałku": 0, "poniedzialek": 0,
    "tuesday": 1, "tue": 1, "wtorek": 1, "wtorku": 1,
    "wednesday": 2, "wed": 2, "środa": 2, "środy": 2, "środę": 2, "sroda": 2, "srody": 2,
    "thursday": 3, "thu": 3, "czwartek": 3, "czwartku": 3,
    "friday": 4, "fri": 4, "piątek": 4, "piątku": 4, "piatek": 4, "piatku": 4,
    "saturday": 5, "sat": 5, "sobota": 5, "soboty": 5,
    "sunday": 6, "sun": 6, "niedziela": 6, "niedzieli": 6,
}

NAME = r"[A-ZĄĆĘŁŃÓŚŹŻ][^\W\d_]{1,24}"
LEAD = r"(?:\b(?:for|by|until|before|on|due|do|na|w|we|przed)\s+)?"

ISO = re.compile(
    r"(?:\b(?:by|until|before|due|do|przed|termin)\s*:?\s*)?(\d{4}-\d{2}-\d{2})\b", re.I
)
DMY = re.compile(
    r"\b(?:by|until|before|due|do|przed|termin)\s*:?\s*(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?(?!\d)",
    re.I,
)
RELATIVE = [
    (re.compile(LEAD + r"\b(?:tomorrow|jutro)\b", re.I), lambda r: r + timedelta(days=1)),
    (
        re.compile(LEAD + r"\b(?:today|dzisiaj|dziś|dzis|eod|end of day|koniec dnia)\b", re.I),
        lambda r: r,
    ),
    (
        re.compile(
            LEAD + r"\b(?:end of (?:the )?week|eow|końca tygodnia|koniec tygodnia)\b", re.I
        ),
        lambda r: r + timedelta(days=(4 - r.weekday()) % 7),
    ),
    (
        re.compile(
            LEAD + r"\b(?:next week|przyszłym tygodniu|przyszły tydzień|przyszłego tygodnia)\b",
            re.I,
        ),
        lambda r: r + timedelta(days=7 - r.weekday() + 4),
    ),
]
WEEKDAY = re.compile(
    r"\b(?:by|until|before|due|on|next|do|przed|na|w)\s+("
    + "|".join(sorted(WEEKDAYS, key=len, reverse=True))
    + r")\b",
    re.I,
)

STOP_OWNERS = {
    "action", "actions", "todo", "decision", "decisions", "note", "notes", "risk", "risks",
    "question", "questions", "agenda", "summary", "next", "blocker", "update", "info",
    "zadanie", "zadania", "decyzja", "decyzje", "ryzyko", "ryzyka", "pytanie", "pytania",
    "uwagi", "notatki", "ustalenia", "podsumowanie", "akcja", "akcje", "priorytet",
    "status", "spotkanie", "meeting", "attendees", "uczestnicy", "obecni", "date", "data",
    "topic", "temat", "owner", "deadline", "termin", "budget", "budżet",
    "we", "i", "you", "they", "it", "he", "she", "this", "that", "there", "who", "my",
    "wy", "oni", "ona", "on", "to", "co", "kto", "ktos", "ktoś", "team", "ma", "musi",
    "robi", "jest", "też", "nie", "juz", "już", "teraz", "now", "and", "then",
}

SECTIONS = {
    "actions": r"action items?|actions?|to-?do|next steps|tasks|zadania|akcje|działania|następne kroki|do zrobienia",
    "decisions": r"decisions?|agreed|resolutions?|decyzje|decyzja|ustalenia|uzgodnienia",
    "risks": r"risks?|risks? (?:&|and) blockers|blockers|concerns|ryzyka|ryzyko|zagrożenia|blokery|obawy",
    "questions": r"(?:open )?questions?|pytania|pytanie|otwarte pytania|do wyjaśnienia",
    "attendees": r"attendees|participants|present|uczestnicy|obecni",
    "other": r"agenda|notes|summary|discussion|overview|notatki|podsumowanie|omówienie|topics|tematy",
}
SECTION_RES = {
    name: re.compile(rf"^(?:{pattern})\s*(?::\s*(?P<rest>.*))?$", re.I)
    for name, pattern in SECTIONS.items()
}

BULLET = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s+")
CHECK = re.compile(r"^\[([ xX])\]\s*")
MARKER = re.compile(r"^(?:todo|to-do|action(?: item)?|ai|zadanie|akcja)\s*[:\-–]\s*", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ@])")

DECISION = re.compile(
    r"^(?:decision|decided|agreed|resolved|we (?:decided|agreed)|decyzja|ustalono|"
    r"zdecydowano|uzgodniono|postanowiono)\b[:\s,-]*(?:(?:to|that|że)\s+)?",
    re.I,
)
RISK = re.compile(r"^(?:risk|concern|ryzyko|obawa|zagrożenie)\b[:\s,-]*|\brisk of\b", re.I)
QUESTION = re.compile(r"^(?:question|open question|pytanie)\b[:\s,-]*", re.I)

CUES = re.compile(
    r"\b(will|should|must|needs? to|todo|to-do|follow[- ]up|prepare|send|review|fix|"
    r"implement|create|update|schedule|draft|investigate|check|deliver|finish|complete|"
    r"write|set up|setup|confirm|contact|organi[sz]e|book|share|deploy|test|migrate|"
    r"refactor|build|add|design|document|plan|resolve|finalize|finalise|research|"
    r"robi|robię|robią|pracuje|zrobic|dodac|naprawic|przygotowac|wyslac|sprawdzic|"
    r"musi|powinien|powinna|trzeba|należy|przygotuj\w*|wyślij\w*|wyśl\w*|napraw\w*|"
    r"zaimplementuj\w*|wdroż\w*|stwórz|stworz\w*|zaktualizuj\w*|zaplanuj\w*|sprawdz\w*|"
    r"sprawdź|dostarcz\w*|dokończ\w*|ukończ\w*|napisz\w*|skontaktuj\w*|zorganizuj\w*|"
    r"udostępnij\w*|przetestuj\w*|zmigruj\w*|zaprojektuj\w*|udokumentuj\w*|rozwiąż\w*|"
    r"zrób|zrobi\w*|zajmie|zbadaj|zbadać|dodaj|dodać|przejrz\w*|omów\w*|potwierdź|"
    r"potwierdz\w*)\b",
    re.I,
)

LABELED_OWNER = re.compile(
    r"\b(?:owner|assignee|assigned to|responsible|właściciel|odpowiedzialn\w+|przypisan\w+ do)"
    r"\s*[:=]?\s*@?(?-i:(" + NAME + r"))",
    re.I,
)
MENTION = re.compile(r"@([^\W\d_][\w.]{1,24})")
TRAILING_OWNER = re.compile(r"\s*\((" + NAME + r")\)\s*[.!]?$")
PREFIX_OWNER = re.compile(r"^(" + NAME + r")\s*[:–—-]\s+(.+)$")
WILL_OWNER = re.compile(
    r"^(" + NAME + r")\s+(?:will|is going to|should|needs to|must|musi|powinien|powinna|"
    r"zajmie się|przygotuje|wyśle|zrobi|sprawdzi|zadba o|skontaktuje się z|zorganizuje|"
    r"dostarczy|ma)\s+(.+)$"
)


STATUS_PREFIX = re.compile(
    r"^(?:w progresie|w progress|in progress|w trakcie|w toku|zrobione|gotowe|done)\s*[:\-–]?\s+",
    re.I,
)
LOOSE_OWNER = re.compile(
    r"^([^\W\d_]{2,24})\s+(?:(?:juz|już|teraz|now|already)\s+)?"
    r"(?:ma|musi|robi|zrobi|pracuje|will|should|must)\s+(.+)$",
    re.I,
)
NAMELESS_OWNER = re.compile(r"^([^\W\d_]{2,24})\s+(.+)$")
LEADING_MODAL = re.compile(r"^(?:ma|musi|will|should|must|needs to)\s+", re.I)
AND_SPLIT = re.compile(
    r"\s+(?:i|oraz|and|then|potem)\s+(?=(?:ma|musi|will|should|must|needs to)\b)", re.I
)
CONTRAST_SPLIT = re.compile(r"\s+a\s+(?=[^\W\d_]{2,24}\s+\S)", re.I)
POLISH_TASK = re.compile(r"\b(?:ma|musi|robi|zrobi\w*|zrobić|zrobic)\b", re.I)


def split_clauses(text: str) -> list[tuple[str, str]]:
    segments = CONTRAST_SPLIT.split(text) if POLISH_TASK.search(text) else [text]
    result = []
    for si, segment in enumerate(segments):
        for pi, piece in enumerate(AND_SPLIT.split(segment)):
            kind = "first" if si == 0 and pi == 0 else "contrast" if pi == 0 else "and"
            result.append((kind, piece.strip()))
    return result


def parse_due(text: str, ref: date) -> tuple[Optional[date], str]:
    m = ISO.search(text)
    if m:
        try:
            return date.fromisoformat(m.group(1)), text[: m.start()] + text[m.end():]
        except ValueError:
            pass
    m = DMY.search(text)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else ref.year
        if year < 100:
            year += 2000
        try:
            found = date(year, month, day)
            if not m.group(3) and found < ref:
                found = date(year + 1, month, day)
            return found, text[: m.start()] + text[m.end():]
        except ValueError:
            pass
    for pattern, resolver in RELATIVE:
        m = pattern.search(text)
        if m:
            return resolver(ref), text[: m.start()] + text[m.end():]
    m = WEEKDAY.search(text)
    if m:
        target = WEEKDAYS[m.group(1).lower()]
        delta = (target - ref.weekday()) % 7 or 7
        return ref + timedelta(days=delta), text[: m.start()] + text[m.end():]
    return None, text


def match_section(line: str) -> Optional[tuple[str, str]]:
    stripped = re.sub(r"^[#*_\s]+|[*_\s]+$", "", line)
    for name, pattern in SECTION_RES.items():
        m = pattern.match(stripped)
        if m:
            return name, (m.group("rest") or "").strip()
    return None


def split_owner(text: str, participants: set[str], in_actions: bool) -> tuple[Optional[str], str]:
    m = LABELED_OWNER.search(text)
    if m:
        return m.group(1), (text[: m.start()] + text[m.end():]).strip(" ,;-")
    m = PREFIX_OWNER.match(text)
    if m and m.group(1).lower() not in STOP_OWNERS:
        rest = m.group(2)
        if m.group(1) in participants or in_actions or CUES.search(rest):
            return m.group(1), rest
    m = WILL_OWNER.match(text)
    if m and m.group(1).lower() not in STOP_OWNERS:
        return m.group(1), m.group(2)
    m = LOOSE_OWNER.match(text)
    if m and m.group(1).lower() not in STOP_OWNERS:
        name = m.group(1)
        return name[:1].upper() + name[1:], m.group(2)
    m = TRAILING_OWNER.search(text)
    if m and m.group(1).lower() not in STOP_OWNERS:
        return m.group(1), text[: m.start()]
    m = MENTION.search(text)
    if m:
        name = m.group(1)
        return name[:1].upper() + name[1:], (text[: m.start()] + text[m.end():]).strip(" ,;-")
    return None, text


def clean_title(text: str) -> str:
    text = HASHTAG.sub("", text)
    text = POINTS.sub("", text)
    for _ in range(2):
        text = STATUS_TAIL.sub("", text)
    text = re.sub(r"(?:\s*,){2,}", ",", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\s,;:–—-]+|[\s,;:–—-]+$", "", text)
    text = LEADING_MODAL.sub("", text)
    text = text.rstrip(".")
    if len(text) > 140:
        text = text[:137].rstrip() + "..."
    return text[:1].upper() + text[1:]


def explicit_points(text: str) -> Optional[int]:
    m = POINTS.search(text)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def sentences(line: str) -> list[str]:
    if len(line) <= 90:
        return [line]
    return [part for part in SENTENCE_SPLIT.split(line) if part.strip()]


def extract(notes: str, ref: date) -> dict:
    participants: set[str] = set()
    for raw in notes.splitlines():
        found = match_section(BULLET.sub("", raw).strip())
        if found and found[0] == "attendees" and found[1]:
            for part in re.split(r"[,;]", found[1]):
                token = part.strip().split(" ")[0] if part.strip() else ""
                if token:
                    participants.add(token)
    for m in MENTION.finditer(notes):
        participants.add(m.group(1)[:1].upper() + m.group(1)[1:])

    decisions: list[str] = []
    risks: list[str] = []
    questions: list[str] = []
    cards: list[Card] = []
    seen: set[str] = set()
    section = "other"

    def add_note(bucket: list[str], text: str) -> None:
        text = text.strip().rstrip(".")
        if text and text not in bucket:
            bucket.append(text[:1].upper() + text[1:])

    def add_card(
        text: str,
        checked: bool,
        forced: bool,
        in_actions: bool,
        owner_hint: Optional[str] = None,
        loose_name: bool = False,
    ) -> Optional[Card]:
        source = text
        prefix = STATUS_PREFIX.match(text)
        if prefix:
            forced = True
            text = text[prefix.end():]
        owner, body = split_owner(text, participants, in_actions)
        if owner is None and owner_hint:
            owner = owner_hint
        if owner is None and loose_name:
            named = NAMELESS_OWNER.match(text)
            if named and named.group(1).lower() not in STOP_OWNERS:
                owner = named.group(1)[:1].upper() + named.group(1)[1:]
                body = named.group(2)
        due, body = parse_due(body, ref)
        has_cue = bool(CUES.search(source))
        if not (forced or in_actions or (owner and has_cue) or (has_cue and due)):
            return None
        labels = [tag.lower() for tag in HASHTAG.findall(body)]
        points = explicit_points(body)
        column = infer_column(source, checked, bool(owner or due))
        title = clean_title(body)
        key = re.sub(r"\W+", " ", title.lower()).strip()
        if len(title) < 3 or key in seen:
            return None
        seen.add(key)
        cards.append(
            make_card(
                len(cards) + 1,
                title,
                owner,
                due,
                column,
                ref,
                source=source,
                points=points,
                labels=labels,
            )
        )
        return cards[-1]

    for raw in notes.splitlines():
        line = raw.strip()
        if not line:
            continue
        found = match_section(BULLET.sub("", line).strip())
        pending: list[tuple[str, str]] = []
        if found:
            name, rest = found
            if name == "attendees":
                continue
            if not rest:
                section = name
                continue
            pending = [(name, rest)]
        else:
            pending = [(section, part) for part in sentences(line)]

        for current, chunk in pending:
            text = BULLET.sub("", chunk).strip()
            checked = False
            forced = False
            m = CHECK.match(text)
            if m:
                checked = m.group(1).lower() == "x"
                forced = True
                text = text[m.end():]
            m = MARKER.match(text)
            if m:
                forced = True
                text = text[m.end():]
            text = text.strip()
            if not text:
                continue

            if current == "attendees":
                continue
            if current == "decisions" or DECISION.match(text):
                add_note(decisions, DECISION.sub("", text))
                continue
            if current == "risks" or RISK.search(text):
                add_note(risks, RISK.sub("", text) if RISK.match(text) else text)
                continue
            if current == "questions" or QUESTION.match(text) or text.endswith("?"):
                add_note(questions, QUESTION.sub("", text))
                continue
            first_owner = None
            for kind, clause in split_clauses(text):
                card = add_card(
                    clause,
                    checked,
                    forced or kind != "first",
                    current == "actions",
                    owner_hint=first_owner if kind == "and" else None,
                    loose_name=kind == "contrast",
                )
                if kind == "first":
                    first_owner = card.owner if card else None

    return {
        "cards": cards,
        "decisions": decisions,
        "risks": risks,
        "questions": questions,
        "participants": sorted(participants),
    }


def from_items(data: dict, ref: date) -> dict:
    cards: list[Card] = []
    for item in data.get("items", []):
        title = clean_title(str(item.get("title", "")))
        if len(title) < 3:
            continue
        due = None
        try:
            due = date.fromisoformat(item["due"]) if item.get("due") else None
        except (ValueError, TypeError):
            due = None
        owner = item.get("owner") or None
        status = str(item.get("status", "")).lower()
        column = {"done": "done", "review": "review", "doing": "doing", "in_progress": "doing"}.get(
            status, "todo" if (owner or due) else "backlog"
        )
        priority = item.get("priority") if item.get("priority") in ("critical", "high", "medium", "low") else None
        kind = item.get("kind") if item.get("kind") in ("task", "bug", "feature", "spike") else None
        points = item.get("points") if isinstance(item.get("points"), int) else None
        cards.append(
            make_card(
                len(cards) + 1,
                title,
                owner,
                due,
                column,
                ref,
                source=title,
                priority=priority,
                kind=kind,
                points=points,
            )
        )
    return {
        "cards": cards,
        "decisions": [str(x) for x in data.get("decisions", [])][:20],
        "risks": [str(x) for x in data.get("risks", [])][:20],
        "questions": [str(x) for x in data.get("questions", [])][:20],
        "participants": [str(x) for x in data.get("participants", [])][:30],
    }
