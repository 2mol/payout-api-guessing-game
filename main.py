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
    api_key_sn: str
    api_key_ci: str
    prize_amount: str
    correct_answer_min: int
    correct_answer_max: int

settings = Settings()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def send_money(*, api_key: str, idempotency_key: str, json_data: Dict[str, str]):
    headers = {
        "authorization": f"Bearer {api_key}",
        # Already added when you pass json= but not when you pass data=
        # "content-type": "application/json",
        "idempotency-key": idempotency_key,
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
    if settings.correct_answer_min <= guess <= settings.correct_answer_max:
        response = send_money(
            api_key = settings.api_key,
            # Using the number as the idempotency key. This way the same
            # wallet can't receive money twice:
            idempotency_key=f_number,
            json_data = {
                "currency": "XOF",
                "receive_amount": settings.prize_amount,
                "name": name,
                "mobile": f_number,
                "client_reference": "all hands api demo",
            },
        )

        if not response.ok:
            response_body = response.json()
            print(response_body)
            err_msg = response_body.get("code", "")
            return f"sorry, something went wrong: {err_msg}"
        else:
            print(f"winner winner, chicken dinner: {name} - {f_number}")
            return "CORRECT!!!"
    else:
        return "wrong answer :("
