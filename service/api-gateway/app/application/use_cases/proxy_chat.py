from app.schemas.proxy import ChatCompletionRequest
from app.domain.guardrails.pii import PIIDetector


def sanitize_last_user_message(request: ChatCompletionRequest) -> ChatCompletionRequest:
    if not request.messages:
        return request

    last_user_message = request.messages[-1].content
    request.messages[-1].content = PIIDetector.mask_pii(last_user_message)
    return request

