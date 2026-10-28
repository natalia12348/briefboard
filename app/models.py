from typing import Literal, Optional

from pydantic import BaseModel, Field

Priority = Literal["critical", "high", "medium", "low"]
Kind = Literal["task", "bug", "feature", "spike"]
Method = Literal["kanban", "scrum", "scrumban"]


class Card(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=240)
    owner: Optional[str] = None
    due: Optional[str] = None
    priority: Priority = "medium"
    kind: Kind = "task"
    points: int = Field(default=3, ge=1, le=21)
    column: str = "backlog"
    labels: list[str] = Field(default_factory=list)
    moscow: str = "Should"
    score: float = 0.0
    source: str = ""


class Column(BaseModel):
    id: str
    title: str
    wip: Optional[int] = None


class Board(BaseModel):
    method: Method = "kanban"
    velocity: int = Field(default=20, ge=1, le=200)
    columns: list[Column]
    cards: list[Card] = Field(default_factory=list, max_length=300)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    notes: str = Field(min_length=1, max_length=20000)
    method: Method = "kanban"
    velocity: int = Field(default=20, ge=1, le=200)
    reference_date: Optional[str] = None
    use_llm: bool = True


class MethodRequest(BaseModel):
    board: Board
    method: Method
    velocity: int = Field(default=20, ge=1, le=200)


class ExportRequest(BaseModel):
    board: Board
    format: Literal["csv", "markdown", "json"]
