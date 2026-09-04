from fastapi import APIRouter, HTTPException
from ..ai.agent import chat
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    try:
        return await chat(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Do not expose stack traces/credentials to frontend.
        raise HTTPException(status_code=503, detail="AI analytics service is temporarily unavailable") from exc


@router.post("/chart", response_model=ChatResponse)
async def agent_chart(request: ChatRequest):
    # Same agent endpoint; chart intent is resolved by the Foundry agent/tool.
    return await agent_chat(request)
