from app.agents.base import BaseAgent


class AnalystAgent(BaseAgent):
    def run(self, input_text: str) -> str:
        return f"Analyst phân tích yêu cầu: {input_text[:200]}"
