from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers.agent import router as agent_router
from .routers.dashboard import router as dashboard_router

settings = get_settings()
app = FastAPI(title="Plug-and-Play Ask AI Table Analytics POC", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)
app.include_router(agent_router)


@app.get("/health")
def health():
    return {"status": "ok"}
