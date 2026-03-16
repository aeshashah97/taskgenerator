from fastapi import APIRouter, HTTPException, Query
from clients.google_client import GoogleClient

router = APIRouter()


@router.get("/google-doc")
def fetch_google_doc(url: str = Query(...)):
    try:
        client = GoogleClient()
        text = client.fetch_doc(url)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
