from typing import Dict

import phonenumbers
import requests
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseSettings

from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))

class Settings(BaseSettings):
    api_key: str
    prize_amount: str
    correct_answer: int

settings = Settings()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def send_money(api_key: str, json_data: Dict[str, str]):
    headers = {
        "authorization": f"Bearer {api_key}",
        # Already added when you pass json= but not when you pass data=
        # "content-type": "application/json",
        "idempotency-key": "00b94729bf0c0c7f",
    }

    response = requests.post('https://api.wave.com/v1/payout', headers=headers, json=json_data)

    return response


@app.get("/")
async def root(request: Request) -> dict:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request},
    )


@app.post("/")
async def root(guess: int = Form(), name: str = Form(), number: str = Form()):
    try:
        p_number = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(p_number):
            return "invalid phone number"
        f_number = phonenumbers.format_number(p_number, phonenumbers.PhoneNumberFormat.E164)
    except:
        return "invalid phone number"
    if guess == settings.correct_answer:
        response = send_money(
            api_key = settings.api_key,
            json_data = {
                "currency": "XOF",
                "receive_amount": settings.prize_amount,
                "name": name,
                "mobile": f_number,
                "client_reference": "all hands api demo",
            },
        )

        return "CORRECT!!!"
    else:
        return "wrong answer :("
