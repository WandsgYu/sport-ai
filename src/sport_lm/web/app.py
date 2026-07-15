from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape


APP_TITLE = "脱敏事件查看器"
EVENTS_FILE = Path("logs") / "events.jsonl"
SAFE_EVENT_FIELDS = {
    "arguments_length",
    "content_length",
    "level",
    "message_length",
    "reason",
    "reply_length",
    "request_id",
    "result_length",
    "scene_ids",
    "stream_id",
    "subject_ref",
    "text_length",
    "tool_call_count",
    "tool_name",
    "ts",
    "type",
}

app = FastAPI(title=APP_TITLE)
_template_dir = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render_template(name: str, context: dict[str, Any]) -> HTMLResponse:
    template = _env.get_template(name)
    return HTMLResponse(template.render(**context))


def _load_events() -> list[dict[str, Any]]:
    """Load only allowlisted metadata even if an old log file contains more."""

    if not EVENTS_FILE.exists():
        return []
    events: list[dict[str, Any]] = []
    with EVENTS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            events.append(
                {key: value for key, value in payload.items() if key in SAFE_EVENT_FIELDS}
            )
    return events


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    level = request.query_params.get("level", "").strip().upper()
    event_type = request.query_params.get("event_type", "").strip()
    events = [
        event
        for event in _load_events()
        if (not level or str(event.get("level", "")).upper() == level)
        and (not event_type or str(event.get("type", "")) == event_type)
    ]
    events.sort(key=lambda event: str(event.get("ts", "")), reverse=True)
    return _render_template(
        "index.html",
        {
            "app_title": APP_TITLE,
            "events": events,
            "filters": {"level": level, "event_type": event_type},
        },
    )


@app.get("/request/{request_id}", response_class=HTMLResponse)
def request_detail(request_id: str) -> HTMLResponse:
    events = [
        event
        for event in _load_events()
        if str(event.get("request_id", "")) == request_id
    ]
    events.sort(key=lambda event: str(event.get("ts", "")))
    return _render_template(
        "detail.html",
        {
            "app_title": APP_TITLE,
            "request_id": request_id,
            "events": events,
        },
    )
