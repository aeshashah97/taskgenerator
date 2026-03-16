import json
import os
from anthropic import Anthropic

HOURS_SENTINEL = 1.0

SYSTEM_PROMPT = """You are a project task extractor. Given a Statement of Work (SOW) or Work Breakdown Structure (WBS) document, extract all tasks and return them as a JSON array.

Each task object must match this exact schema:
{
  "task_name": "string (required)",
  "description": "string (required)",
  "assignee_name": "string or null",
  "estimated_hours": "number (required, min 0.5, max 999)",
  "billing_type": "billable or non-billable (required)",
  "sprint_milestone": "string or null",
  "priority": "high, medium, low, or null",
  "dependencies": ["array of task_name strings"],
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null"
}

Rules:
- Return ONLY a valid JSON array. No prose, no markdown, no explanation.
- Default billing_type to "billable" when ambiguous.
- Set estimated_hours to 1.0 if not determinable from the SOW.
- Set all other optional fields to null if not determinable.
- Only suggest assignee_name values from the provided team members list.
- dependencies should reference task_name values of other tasks in the output."""


class ClaudeClient:
    def __init__(self):
        self._anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    def extract_tasks(self, sow_text: str, team_members: list[str]) -> list[dict]:
        team_members_text = (
            f"Team members available for assignment: {', '.join(team_members)}"
            if team_members
            else "No team members provided — leave assignee_name as null."
        )
        user_content = f"{team_members_text}\n\nSOW/WBS document:\n{sow_text}"

        message = self._anthropic.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = message.content[0].text
        try:
            result = json.loads(raw)
            if not isinstance(result, list):
                raise ValueError(f"parse_failed: expected JSON array, got object. raw_response: {raw}")
            return result
        except json.JSONDecodeError:
            raise ValueError(f"parse_failed: invalid JSON from Claude. raw_response: {raw}")
