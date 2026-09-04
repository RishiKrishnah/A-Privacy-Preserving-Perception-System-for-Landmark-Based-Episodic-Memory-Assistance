from __future__ import annotations

import os
from google import genai


SYSTEM_INSTRUCTION = """You are a privacy-preserving episodic memory assistant.

Answer only from the supplied semantic memory records and the user's question.
Do not claim to have seen images, video, camera frames, or information that is
not present in the records.
If the records do not contain enough evidence, say that the available memory
does not provide enough information.
Prefer concise, simple, direct answers and include relevant time/location details when
available, necessary and asked.
"""


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "replace_me":
            raise RuntimeError("GEMINI_API_KEY is not configured on the server.")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=api_key)

    def answer(self, question: str, memories: list[dict]) -> str:
        context_lines = []
        for m in memories:
            context_lines.append(
                f"- time={m.get('timestamp')}; subject={m.get('subject')}; "
                f"action={m.get('action')}; landmark={m.get('landmark')}; "
                f"details={m.get('details')}"
            )

        context = "\n".join(context_lines) or "(No relevant memories found.)"
        prompt = (
            f"User question:\n{question}\n\n"
            f"Retrieved semantic memories:\n{context}\n\n"
            "Answer the question using only these memories."
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"system_instruction": SYSTEM_INSTRUCTION},
        )
        return (response.text or "").strip()
