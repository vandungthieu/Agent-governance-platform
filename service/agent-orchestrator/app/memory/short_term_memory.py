from __future__ import annotations

from collections import OrderedDict
from threading import Lock


class ShortTermMemory:
    def __init__(self, max_sessions: int = 500, max_turns_per_session: int = 8) -> None:
        self.max_sessions = max_sessions
        self.max_turns_per_session = max_turns_per_session
        self._turns_by_key: OrderedDict[str, list[str]] = OrderedDict()
        self._lock = Lock()

    def session_key(self, user_id: str | None, session_id: str | None) -> str | None:
        identity = session_id or user_id
        return identity.strip() if identity else None

    def recall_context(self, user_id: str | None = None, session_id: str | None = None) -> str:
        key = self.session_key(user_id=user_id, session_id=session_id)
        if not key:
            return ""

        with self._lock:
            turns = self._turns_by_key.get(key)
            if not turns:
                return ""
            self._turns_by_key.move_to_end(key)
            return "\n\n".join(turns[-self.max_turns_per_session :])

    def remember_turn(
        self,
        input_text: str,
        final_answer: str,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        key = self.session_key(user_id=user_id, session_id=session_id)
        if not key:
            return

        turn = f"user: {input_text}\nassistant: {final_answer}".strip()
        with self._lock:
            turns = self._turns_by_key.setdefault(key, [])
            turns.append(turn)
            del turns[:-self.max_turns_per_session]
            self._turns_by_key.move_to_end(key)

            while len(self._turns_by_key) > self.max_sessions:
                self._turns_by_key.popitem(last=False)
