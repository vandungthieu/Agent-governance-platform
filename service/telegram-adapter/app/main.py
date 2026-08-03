from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException, Request, status

from app.clients.agent import AgentClient
from app.clients.telegram import TelegramClient
from app.core.config import settings
from app.schemas import TelegramUpdate


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [telegram-adapter] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)
agent_client = AgentClient()
telegram_client = TelegramClient()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

    payload = await request.json()
    update = TelegramUpdate.model_validate(payload)
    message = update.effective_message()
    if message is None:
        logger.info("ignored_update update_id=%s reason=no_message", update.update_id)
        return {"ok": True}

    chat_id = message.chat.id
    telegram_user_id = message.from_user.id if message.from_user is not None else chat_id
    text = (message.text or "").strip()
    if not text:
        await telegram_client.send_message(chat_id=chat_id, text="Bot hien chi ho tro tin nhan van ban.")
        return {"ok": True}

    session_id = f"telegram:{chat_id}"
    user_id = f"telegram:{telegram_user_id}"
    logger.info(
        "telegram_request update_id=%s chat_id=%s user_id=%s text_length=%s",
        update.update_id,
        chat_id,
        telegram_user_id,
        len(text),
    )

    try:
        answer = await agent_client.run(input_text=text, session_id=session_id, user_id=user_id)
    except Exception:
        logger.exception("agent_request_failed update_id=%s chat_id=%s", update.update_id, chat_id)
        answer = "He thong dang gap loi khi xu ly yeu cau. Vui long thu lai sau."

    await telegram_client.send_message(chat_id=chat_id, text=answer)
    return {"ok": True}
