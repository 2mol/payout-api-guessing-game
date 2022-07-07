from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseSettings

from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))

class Settings(BaseSettings):
    correct_answer: int

settings = Settings()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root(request: Request) -> dict:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request},
    )

@app.post("/guess")
async def guess(guess: int = Form(), name: str = Form(), number: str = Form()):
    if guess == settings.correct_answer:
        return "CORRECT!!!"
    else:
        return f"no :( it was {settings.correct_answer}, but you gave {number}"
