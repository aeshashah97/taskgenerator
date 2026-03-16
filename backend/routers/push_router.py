import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient
from models.task import PushRequest, PushResponse, PushTaskResult

router = APIRouter()

BILLING_MAP = {"billable": "1", "non-billable": "2"}
PRIORITY_MAP = {"high": "1", "medium": "2", "low": "3"}


def _resolve_assignee(
    assignee_name: str | None, members: list[dict]
) -> tuple[str | None, str | None]:
    """Returns (zoho_user_id, warning_message)."""
    if not assignee_name:
        return None, None
    for m in members:
        if m["name"].lower() == assignee_name.lower():
            return m["id"], None
    return (
        None,
        f"Assignee '{assignee_name}' not found in project members — task created without assignee",
    )


def _resolve_milestone(
    milestone_name: str | None, milestones: list[dict]
) -> tuple[str | None, str | None]:
    """Returns (zoho_milestone_id, warning_message)."""
    if not milestone_name:
        return None, None
    for m in milestones:
        if m["name"].lower() == milestone_name.lower():
            return m["id"], None
    return None, f"Milestone '{milestone_name}' not found in project — field dropped"


def _build_task_payload(task, assignee_id: str | None, milestone_id: str | None) -> dict:
    payload = {
        "name": task.task_name,
        "description": task.description,
        "duration": str(task.estimated_hours),
        "billing_type": BILLING_MAP[task.billing_type],
    }
    if assignee_id:
        payload["person_responsible"] = assignee_id
    if milestone_id:
        payload["milestone_id"] = milestone_id
    if task.priority:
        payload["priority"] = PRIORITY_MAP[task.priority]
    if task.start_date:
        payload["start_date"] = task.start_date
    if task.end_date:
        payload["end_date"] = task.end_date
    return payload


@router.post("/push", response_model=PushResponse)
def push_tasks(request: PushRequest):
    try:
        zoho = ZohoClient()
        members = zoho.get_members(request.project_id)
        milestones = zoho.get_milestones(request.project_id)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")

    results: list[PushTaskResult] = []
    name_to_zoho_id: dict[str, str] = {}

    # Pass 1: create all tasks independently
    for task in request.tasks:
        warnings = []
        assignee_id, aw = _resolve_assignee(task.assignee_name, members)
        if aw:
            warnings.append(aw)
        milestone_id, mw = _resolve_milestone(task.sprint_milestone, milestones)
        if mw:
            warnings.append(mw)
        try:
            payload = _build_task_payload(task, assignee_id, milestone_id)
            zoho_task = zoho.create_task(request.project_id, payload)
            zoho_id = zoho_task.get("id_string") or zoho_task.get("id")
            name_to_zoho_id[task.task_name] = zoho_id
            status = "warning" if warnings else "created"
            results.append(PushTaskResult(
                row_id=task.row_id,
                task_name=task.task_name,
                status=status,
                zoho_task_id=zoho_id,
                warnings=warnings,
            ))
        except Exception as e:
            results.append(PushTaskResult(
                row_id=task.row_id,
                task_name=task.task_name,
                status="failed",
                warnings=warnings,
                error=str(e),
            ))

    # Pass 2: link dependencies
    for task in request.tasks:
        if not task.dependencies:
            continue
        result = next((r for r in results if r.row_id == task.row_id), None)
        # Skip pass 2 entirely for tasks that failed in pass 1
        if not result or result.status == "failed":
            continue
        task_zoho_id = result.zoho_task_id
        for dep_name in task.dependencies:
            dep_zoho_id = name_to_zoho_id.get(dep_name)
            if not dep_zoho_id:
                result.warnings.append(
                    f"Dependency '{dep_name}' could not be linked: source task failed to create or was not found"
                )
                if result.status == "created":
                    result.status = "warning"
                continue
            try:
                zoho.add_dependency(request.project_id, task_zoho_id, dep_zoho_id)
            except Exception as e:
                result.warnings.append(f"Failed to link dependency '{dep_name}': {e}")
                if result.status == "created":
                    result.status = "warning"

    return PushResponse(results=results)
