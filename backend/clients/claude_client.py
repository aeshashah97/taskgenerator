import json
import os
from groq import Groq

HOURS_SENTINEL = 1.0

SYSTEM_PROMPT = """You are a senior project manager. Given a Statement of Work (SOW) or Work Breakdown Structure (WBS) document, produce an exhaustive, granular task list that covers every deliverable, feature, and activity mentioned in the document — nothing must be omitted.

Your analysis must:
1. Read the entire document before producing any output. Do not stop early.
2. For every deliverable, feature, module, or activity mentioned in the document, break it down into its constituent WBS tasks. Every item in the SOW must appear as one or more tasks. If something is mentioned in the SOW, it must be in the output.
3. For each deliverable, always include ALL of the following sub-tasks that apply — skip only if clearly irrelevant to that deliverable:
   - Requirements / analysis
   - Design (UI/UX if user-facing; system/API design if backend)
   - Implementation (split into backend and frontend sub-tasks if both are involved)
   - Unit and integration testing
   - Deployment / release
   - Documentation (if the SOW mentions docs or handover)
4. Estimate hours for every task — never leave hours null. Use these baselines:
   requirements/analysis ~4–8h, UI/UX design ~8–16h, backend development ~8–40h, frontend development ~8–24h, API integration ~4–16h, testing ~4–16h, deployment ~2–8h, documentation ~2–8h.

Each task object must match this exact schema:
{
  "task_name": "string (required, concise and specific, prefixed with the deliverable name for clarity e.g. 'User Auth — Backend Implementation')",
  "description": "string (required, 1–2 sentences explaining what needs to be done)",
  "assignee_name": null,
  "estimated_hours": "number (required, min 0.5, max 999)",
  "billing_type": "billable or non-billable (required)",
  "priority": "high, medium, low, or null",
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null"
}

Return format: {"tasks": [...]}

Rules:
- Return ONLY valid JSON. No prose, no markdown, no explanation.
- Default billing_type to "billable" when ambiguous.
- Set optional fields to null if not determinable from the document.
- assignee_name is always null.
- A short SOW with 5 deliverables should produce at least 20–30 tasks. Err on the side of more tasks, not fewer."""


class ClaudeClient:
    def __init__(self):
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

    def extract_tasks(self, sow_text: str, team_members: list[str]) -> list[dict]:
        user_content = f"SOW/WBS document:\n{sow_text}"

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
            seed=42,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0].strip()

        try:
            result = json.loads(raw)
            if isinstance(result, dict) and "tasks" in result:
                result = result["tasks"]
            if not isinstance(result, list):
                raise ValueError(f"parse_failed: expected JSON array or {{tasks:[]}}, got: {raw}")
            return result
        except json.JSONDecodeError:
            raise ValueError(f"parse_failed: invalid JSON from Groq. raw_response: {raw}")
