from typing import Dict

import asyncio
import phonenumbers
import requests
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from sse_starlette.sse import EventSourceResponse

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


@app.get("/")
async def root_get(request: Request) -> dict:
    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request},
    )


@app.post("/")
async def root_post(request: Request, guess: int = Form(), name: str = Form(), number: str = Form()):
    api_key = None
    try:
        p_number = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(p_number):
            return TEMPLATES.TemplateResponse(
                "result.html",
                {"request": request, "txt": "invalid phone number"},
            )
        f_number = phonenumbers.format_number(p_number, phonenumbers.PhoneNumberFormat.E164)

        if p_number.country_code == 221:
            api_key = settings.api_key_sn
        elif p_number.country_code == 225:
            api_key = settings.api_key_ci
    except:
        return TEMPLATES.TemplateResponse(
            "result.html",
            {"request": request, "txt": "invalid phone number"},
        )

    if api_key is None:
        return TEMPLATES.TemplateResponse(
            "result.html",
            {"request": request, "txt": "only SN and CI mobiles supported, sorry!"},
        )



    # ========================================================================
    #      IF THE ANSWER IS CORRECT, SEND MONEY TO THE PROVIDED NUMBER:
    # ========================================================================

    if settings.correct_answer_min <= guess <= settings.correct_answer_max:
        response = requests.post(
            'https://api.wave.com/v1/payout',
            headers = {
                "authorization": f"Bearer {api_key}",
                "idempotency-key": f_number,
            },
            json = {
                "currency": "XOF",
                "receive_amount": settings.prize_amount,
                "name": name,
                "mobile": f_number,
                "client_reference": "all hands api demo",
            }
        )

        # ====================================================================



        if not response.ok:
            response_body = response.json()
            print(response_body)
            err_msg = response_body.get("code", "")

            if err_msg == 'insufficient-funds':
                return TEMPLATES.TemplateResponse(
                    "result.html",
                    {"request": request, "txt": "sorry, you were too slow. all the prizes are already paid out"},
                )
            elif err_msg == 'recipient-limit-exceeded':
                return TEMPLATES.TemplateResponse(
                    "result.html",
                    {"request": request, "txt": "sorry, you were either too slow, or your wallet limit was reached :/"},
                )

            return TEMPLATES.TemplateResponse(
                "result.html",
                {"request": request, "txt": err_msg},
            )
        else:
            print(f"winner winner, chicken dinner: {name} - {f_number}")
            return TEMPLATES.TemplateResponse(
                "result.html",
                {"request": request, "txt": "You win :) Check your Wave app to see if you've received the money."},
            )
    else:
        return TEMPLATES.TemplateResponse(
            "result.html",
            {"request": request, "txt": "wrong answer :("},
        )


STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond

@app.get('/stream')
async def message_stream(request: Request):
    # def new_messages():
    #     # Add logic here to check for new messages
    #     yield 'Hello World'
    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            # if new_messages():
            yield {
                "event": "stream",
                # "id": "message_id",
                # "retry": RETRY_TIMEOUT,
                "data": "message_content"
            }

            await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())
