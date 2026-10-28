from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import agile, exporter, extractor, llm
from .cards import parse_date, rescore
from .models import AnalyzeRequest, Board, ExportRequest, MethodRequest
from .playbook import PLAYBOOK
from .sample import SAMPLES

app = FastAPI(title="Briefboard", docs_url=None, redoc_url=None)


def reference(value) -> date:
    return parse_date(value) or date.today()


def finish(board: Board, today: date) -> dict:
    for card in board.cards:
        rescore(card, today)
    agile.order_cards(board)
    return {"board": board.model_dump(), "metrics": agile.metrics(board, today)}


@app.get("/api/health")
def health():
    return {"status": "ok", "llm": llm.configured()}


@app.get("/api/sample")
def sample(lang: str = "en"):
    return {"notes": SAMPLES.get(lang, SAMPLES["en"])}


@app.get("/api/playbook")
def playbook():
    return PLAYBOOK


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    today = reference(req.reference_date)
    data = None
    engine = "rules"
    if req.use_llm and llm.configured():
        raw = llm.extract(req.notes, today)
        if raw:
            data = extractor.from_items(raw, today)
            engine = "llm"
    if data is None:
        data = extractor.extract(req.notes, today)
    if not data["cards"]:
        raise HTTPException(422, "No action items found. Add owners, verbs or an Action items section.")
    board = Board(
        method=req.method,
        velocity=req.velocity,
        columns=agile.columns_for(req.method),
        cards=data["cards"],
        decisions=data["decisions"],
        risks=data["risks"],
        questions=data["questions"],
        participants=data["participants"],
    )
    agile.apply_method(board, req.method, req.velocity)
    result = finish(board, today)
    result["engine"] = engine
    return result


@app.post("/api/refresh")
def refresh(board: Board):
    return finish(board, date.today())


@app.post("/api/method")
def method(req: MethodRequest):
    board = agile.apply_method(req.board, req.method, req.velocity)
    return finish(board, date.today())


@app.post("/api/export")
def export(req: ExportRequest):
    render, media = exporter.RENDERERS[req.format]
    return Response(render(req.board), media_type=media)


@app.exception_handler(ValueError)
def value_error(_, exc: ValueError):
    return JSONResponse({"detail": str(exc)}, status_code=422)


PUBLIC = Path(__file__).resolve().parent.parent / "public"
if PUBLIC.exists():
    app.mount("/", StaticFiles(directory=PUBLIC, html=True), name="public")
