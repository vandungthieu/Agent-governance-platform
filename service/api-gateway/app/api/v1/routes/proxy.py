from fastapi import APIRouter, HTTPException, status
import httpx

from app.application.use_cases.proxy_chat import sanitize_last_user_message
from app.schemas.proxy import ChatCompletionRequest
from app.core.config import settings

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request = sanitize_last_user_message(request)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=request.model_dump(),
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Upstream LLM Error: {response.text}",
                )

            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Error connecting to LLM provider: {str(exc)}",
            )

