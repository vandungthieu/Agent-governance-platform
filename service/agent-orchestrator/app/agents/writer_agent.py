from app.agents.base import BaseAgent


class WriterAgent(BaseAgent):
    def run(self, input_text: str) -> str:
        return f"Writer soạn câu trả lời dựa trên yêu cầu: {input_text[:200]}"
