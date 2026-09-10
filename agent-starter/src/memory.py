from collections import defaultdict
from threading import Lock
from typing import Dict, List


class SessionMemory:
    """Small in-memory conversation store for a single application process."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self._lock = Lock()

    def get(self, session_id: str) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def add(self, session_id: str, prompt: str, response: str) -> None:
        with self._lock:
            turns = self._sessions[session_id]
            turns.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ])
            self._sessions[session_id] = turns[-self.max_turns * 2:]
