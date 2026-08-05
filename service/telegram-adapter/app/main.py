from __future__ import annotations

import logging
from collections import OrderedDict
from threading import Lock

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status

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
processed_updates: OrderedDict[int, None] = OrderedDict()
processed_updates_lock = Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.post("/telegram/webhook")
async def telegram_webhook(
    background_tasks: BackgroundTasks,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram webhook secret")

    payload = await request.json()
    update = TelegramUpdate.model_validate(payload)
    if is_duplicate_update(update.update_id):
        logger.info("ignored_update update_id=%s reason=duplicate", update.update_id)
        return {"ok": True}

    message = update.effective_message()
    if message is None:
        logger.info("ignored_update update_id=%s reason=no_message", update.update_id)
        return {"ok": True}

    chat_id = message.chat.id
    telegram_user_id = message.from_user.id if message.from_user is not None else chat_id
    text = (message.text or "").strip()
    if not text:
        background_tasks.add_task(
            send_telegram_message_safely,
            chat_id=chat_id,
            text="Bot hien chi ho tro tin nhan van ban.",
        )
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

    background_tasks.add_task(
        process_text_message,
        update_id=update.update_id,
        chat_id=chat_id,
        input_text=text,
        session_id=session_id,
        user_id=user_id,
    )
    return {"ok": True}


def is_duplicate_update(update_id: int) -> bool:
    with processed_updates_lock:
        if update_id in processed_updates:
            return True
        processed_updates[update_id] = None
        processed_updates.move_to_end(update_id)
        while len(processed_updates) > settings.PROCESSED_UPDATE_CACHE_SIZE:
            processed_updates.popitem(last=False)
        return False


async def process_text_message(
    *,
    update_id: int,
    chat_id: int,
    input_text: str,
    session_id: str,
    user_id: str,
) -> None:
    try:
        answer = await agent_client.run(input_text=input_text, session_id=session_id, user_id=user_id)
    except Exception:
        logger.exception("agent_request_failed update_id=%s chat_id=%s", update_id, chat_id)
        answer = "He thong dang gap loi khi xu ly yeu cau. Vui long thu lai sau."

    await send_telegram_message_safely(chat_id=chat_id, text=answer)


async def send_telegram_message_safely(*, chat_id: int, text: str) -> None:
    try:
        await telegram_client.send_message(chat_id=chat_id, text=text)
    except Exception:
        logger.exception("telegram_send_failed chat_id=%s", chat_id)
