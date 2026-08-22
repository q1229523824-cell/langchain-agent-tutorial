"""CS2 智能复盘教练的 FastAPI 与网页入口。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from chapter07_cs2_coach.models import (
    AnalysisRequest,
    AnalysisResponse,
    MatchRecord,
)
from chapter07_cs2_coach.runtime import CS2CoachRuntime


WEB_DIRECTORY = Path(__file__).resolve().parent / "web"
MAX_JSON_BYTES = 2 * 1024 * 1024


def create_app(runtime: CS2CoachRuntime | None = None) -> FastAPI:
    runtime = runtime or CS2CoachRuntime.create()
    app = FastAPI(
        title="RoundMind CS2 智能复盘教练",
        version="1.0.0",
        description="用受控 Agent 工作流把比赛事实转化为可追溯的训练建议。",
    )
    app.state.runtime = runtime
    app.mount("/static", StaticFiles(directory=WEB_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    def homepage() -> FileResponse:
        return FileResponse(WEB_DIRECTORY / "index.html")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "roundmind-cs2-coach"}

    @app.get("/api/matches", response_model=list[MatchRecord], tags=["matches"])
    def list_matches() -> list[MatchRecord]:
        return runtime.repository.list()

    @app.post("/api/matches", response_model=MatchRecord, tags=["matches"])
    def add_match(match: MatchRecord) -> MatchRecord:
        return runtime.add_match(match)

    @app.post("/api/upload-json", response_model=MatchRecord, tags=["matches"])
    async def upload_json(file: UploadFile = File(...)) -> MatchRecord:
        if not file.filename or not file.filename.lower().endswith(".json"):
            raise HTTPException(status_code=400, detail="MVP 目前只接受 .json 比赛文件。")
        content = await file.read(MAX_JSON_BYTES + 1)
        if len(content) > MAX_JSON_BYTES:
            raise HTTPException(status_code=413, detail="JSON 文件不能超过 2 MB。")
        try:
            payload = json.loads(content.decode("utf-8"))
            match = MatchRecord.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
            raise HTTPException(status_code=422, detail=f"比赛文件格式无效：{error}") from error
        return runtime.add_match(match)

    @app.post("/api/analyze", response_model=AnalysisResponse, tags=["agent"])
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        try:
            return runtime.analyze(match_id=request.match_id, question=request.question)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return app


app = create_app()
