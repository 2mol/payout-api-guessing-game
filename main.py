import databases
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
DATABASE_URL = "sqlite+aiosqlite:///database.db"

database = databases.Database(DATABASE_URL)

class Settings(BaseSettings):
    api_key_sn: str
    api_key_ci: str
    prize_amount: str
    correct_answer_min: int
    correct_answer_max: int

settings = Settings()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def database_connect():
    await database.connect()

    pragmas = [
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous  = NORMAL",
        "PRAGMA cache_size   = -64000",
        "PRAGMA busy_timeout = 5000",
    ]

    for pragma_query in pragmas:
        await database.execute(query=pragma_query)


@app.on_event("shutdown")
async def database_disconnect():
    await database.disconnect()


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


STREAM_DELAY = 0.5  # seconds
RETRY_TIMEOUT = 15000  # miliseconds

PARTY_EMOJIS = ["🎊", "🎉", "🥳"]


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

            query = """
                select id, data
                from data
                order by id desc
                limit 100;
            """

            rows = await database.fetch_all(query=query)
            if len(rows) > 0:
                msg_data = "\n".join([
                    f"<div>{PARTY_EMOJIS[id % len(PARTY_EMOJIS)]} {data}</div>"
                    for (id, data) in rows
                ])

                # Checks for new messages and return them to client if any
                # if new_messages():
                yield {
                    "event": "message",
                    # "id": "message_id",
                    # "retry": RETRY_TIMEOUT,
                    "data": msg_data
                }

            await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())
