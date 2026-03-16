import httpx
from fastapi import APIRouter, HTTPException
from clients.zoho_client import ZohoClient

router = APIRouter(prefix="/zoho")


@router.get("/projects")
def get_projects():
    try:
        client = ZohoClient()
        projects = client.get_projects()
        return {"projects": [{"id": p["id_string"], "name": p["name"]} for p in projects]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")


@router.get("/projects/{project_id}/members")
def get_members(project_id: str):
    try:
        client = ZohoClient()
        members = client.get_members(project_id)
        return {"members": [{"id": m["id"], "name": m["full_name"]} for m in members]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")


@router.get("/projects/{project_id}/milestones")
def get_milestones(project_id: str):
    try:
        client = ZohoClient()
        milestones = client.get_milestones(project_id)
        return {"milestones": [{"id": m["id_string"], "name": m["name"]} for m in milestones]}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Zoho API unavailable: {e}")
