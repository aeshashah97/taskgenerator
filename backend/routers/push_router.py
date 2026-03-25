import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient
from models.task import PushRequest, PushResponse, PushTaskResult

router = APIRouter()

PRIORITY_MAP = {"high": "High", "medium": "Medium", "low": "Low"}


def _resolve_assignees(
    assignee_names: list[str], members: list[dict]
) -> tuple[str | None, list[str]]:
    """Returns (comma_separated_ids_or_None, warnings)."""
    if not assignee_names:
        return None, []
    resolved_ids = []
    warnings = []
    for name in assignee_names:
        for m in members:
            if m["name"].lower() == name.lower():
                resolved_ids.append(m["id"])
                break
        else:
            warnings.append(
                f"Assignee '{name}' not found in project members — skipped"
            )
    return (",".join(resolved_ids) if resolved_ids else None), warnings


def _zoho_date(iso_date: str | None) -> str | None:
    """Convert YYYY-MM-DD to MM-DD-YYYY for Zoho."""
    if not iso_date:
        return None
    try:
        y, m, d = iso_date.split("-")
        return f"{m}-{d}-{y}"
    except Exception:
        return None


def _build_task_payload(task, assignee_ids: str | None) -> dict:
    payload = {
        "name": task.task_name,
        "description": task.description,
    }
    if task.estimated_hours:
        payload["duration"] = str(round(task.estimated_hours / 8, 2))
    if assignee_ids:
        payload["person_responsible"] = assignee_ids
    if task.priority:
        payload["priority"] = PRIORITY_MAP[task.priority]
    start = _zoho_date(task.start_date)
    if start:
        payload["start_date"] = start
    end = _zoho_date(task.end_date)
    if end:
        payload["end_date"] = end
    return payload


@router.post("/push", response_model=PushResponse)
def push_tasks(request: PushRequest):
    try:
        zoho = ZohoClient()
        members = zoho.get_members(request.project_id)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")

    results: list[PushTaskResult] = []
    name_to_zoho_id: dict[str, str] = {}
    failed_task_names: set[str] = set()

    # Pass 1: create all tasks independently
    for task in request.tasks:
        warnings = []
        assignee_ids, aws = _resolve_assignees(task.assignee_names, members)
        warnings.extend(aws)
        try:
            payload = _build_task_payload(task, assignee_ids)
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
            failed_task_names.add(task.task_name)
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
        if not result or result.status == "failed":
            continue
        task_zoho_id = result.zoho_task_id
        for dep_name in task.dependencies:
            dep_zoho_id = name_to_zoho_id.get(dep_name)
            if not dep_zoho_id:
                if dep_name in failed_task_names:
                    result.warnings.append(
                        f"dependency '{dep_name}' could not be linked: source task failed to create"
                    )
                else:
                    result.warnings.append(
                        f"dependency '{dep_name}' could not be linked: source task not found"
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
