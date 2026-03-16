import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers.zoho_router import router as zoho_router
from routers.extract_router import router as extract_router
from routers.push_router import router as push_router
from routers.google_router import router as google_router

load_dotenv()

app = FastAPI(title="SOW Task Generator")

origins = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zoho_router)
app.include_router(extract_router)
app.include_router(push_router)
app.include_router(google_router)
