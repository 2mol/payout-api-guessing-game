from fastapi import FastAPI, APIRouter, Query, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from typing import Optional, Any
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(request: Request) -> dict:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {},
    )

@app.post("/guess")
async def guess(name: str = Form(), number: str = Form()):
    return {"name": name, "number": number}
