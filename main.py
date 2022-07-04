from fastapi import FastAPI, APIRouter, Query, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from typing import Optional, Any
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))


app = FastAPI()

app.mount("/css", StaticFiles(directory="css"), name="css")

@app.get("/")
async def root(request: Request) -> dict:
    print("sasasa")
    return TEMPLATES.TemplateResponse(
        "index.html",
        {
            "request": request,
        },
    )

@app.post("/guess")
async def guess(name: str = Form(), number: str = Form()):
    print("sasasa")
    return {"name": name, "number": number}
