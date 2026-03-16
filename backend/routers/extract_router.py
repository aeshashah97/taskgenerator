from fastapi import APIRouter
from fastapi.responses import JSONResponse
from clients.claude_client import ClaudeClient
from models.task import ExtractRequest, ExtractResponse

router = APIRouter()


@router.post("/extract")
def extract_tasks(request: ExtractRequest):
    try:
        client = ClaudeClient()
        raw_tasks = client.extract_tasks(request.sow_text, request.team_members)
        return ExtractResponse(tasks=raw_tasks)
    except ValueError as e:
        raw = str(e).replace("parse_failed: ", "", 1)
        return JSONResponse(
            status_code=422,
            content={"error": "parse_failed", "raw_response": raw},
        )
