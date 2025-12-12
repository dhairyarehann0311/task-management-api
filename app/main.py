from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.api.routes import analytics, auth, tasks, timeline

app = FastAPI(
    title="Task Management API",
    default_response_class=ORJSONResponse,
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(timeline.router)


@app.get("/health")
async def health():
    return {"ok": True}
