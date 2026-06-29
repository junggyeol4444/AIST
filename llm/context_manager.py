"""Conversation context management.

Keeps a sliding window of recent turns so an 8-hour broadcast does not blow up
memory. Older turns are dropped (and optionally folded into a lightweight text
summary that a future phase can replace with an LLM-generated summary).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Turn:
    role: str          # "assistant" (streamer) | "user" (viewer/system)
    name: str          # display name (streamer name, viewer nickname, ...)
    content: str
    ts: float = field(default_factory=time.time)


class ConversationContext:
    """Sliding-window conversation history.

    Parameters
    ----------
    max_turns:
        Number of most-recent turns kept verbatim and sent to the model.
    """

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self._turns: list[Turn] = []
        self.summary: str = ""

    def add(self, role: str, name: str, content: str) -> None:
        self._turns.append(Turn(role=role, name=name, content=content.strip()))
        self._trim()

    def add_viewer_chat(self, nickname: str, content: str) -> None:
        self.add("user", nickname, content)

    def add_streamer_speech(self, name: str, content: str) -> None:
        self.add("assistant", name, content)

    def _trim(self) -> None:
        overflow = len(self._turns) - self.max_turns
        if overflow > 0:
            dropped = self._turns[:overflow]
            self._turns = self._turns[overflow:]
            self._fold_into_summary(dropped)

    def _fold_into_summary(self, dropped: Iterable[Turn]) -> None:
        # Naive summary: keep a short trailing breadcrumb of dropped topics.
        # Phase 5 replaces this with a periodic LLM summarization pass.
        snippets = [f"{t.name}: {t.content[:30]}" for t in dropped]
        if snippets:
            joined = " / ".join(snippets)
            self.summary = (self.summary + " | " + joined)[-600:].lstrip(" |")

    @property
    def turns(self) -> list[Turn]:
        return list(self._turns)

    def recent(self, n: int) -> list[Turn]:
        return self._turns[-n:]

    def recent_streamer_utterances(self, n: int = 5) -> list[str]:
        """Most recent streamer lines — used to discourage repetition."""
        out = [t.content for t in self._turns if t.role == "assistant"]
        return out[-n:]

    def as_messages(self) -> list[dict[str, str]]:
        """Render the window as OpenAI/Ollama-style chat messages.

        Viewer turns are prefixed with the nickname so the model can tell who
        said what; streamer turns are plain assistant messages.
        """
        messages: list[dict[str, str]] = []
        for t in self._turns:
            if t.role == "assistant":
                messages.append({"role": "assistant", "content": t.content})
            else:
                messages.append({"role": "user", "content": f"[{t.name}] {t.content}"})
        return messages

    def __len__(self) -> int:
        return len(self._turns)
