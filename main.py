import databases
import asyncio
import phonenumbers
import random
import requests
from fastapi import BackgroundTasks, FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseSettings
from sse_starlette.sse import EventSourceResponse

from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))
DATABASE_URL = "sqlite+aiosqlite:///database.db"

STREAM_DELAY = 0.5  # seconds
RETRY_TIMEOUT = 15000  # miliseconds

PARTY_EMOJIS = ["🎊", "🎉", "🥳"]

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
    query = """
        select data
        from data
        where has_been_broadcast
        order by id desc
        limit 100;
    """

    rows = await database.fetch_all(query=query)
    messages = [data for (data,) in rows]

    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request, "messages": messages},
    )


async def post_message(message: str):
    await database.execute(query="insert into data (data) values (:msg)", values={"msg": message})


def win(request, background_tasks, name, win_amount):
    win_msg = f"{random.choice(PARTY_EMOJIS)} {name} wins {win_amount} CFA!!"
    background_tasks.add_task(post_message, message=win_msg)
    return TEMPLATES.TemplateResponse(
        "result.html",
        {"request": request, "txt": "You win :) Check your Wave app to see if you've received the money."},
    )

@app.post("/")
async def root_post(
    request: Request,
    background_tasks: BackgroundTasks,
    guess: int = Form(),
    name: str = Form(),
    number: str = Form(),
):
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

    # some aliases to make the code example below more readable:
    recipient_name = name
    mobile_number = f_number
    correct_answer_minimum = settings.correct_answer_min
    correct_answer_maximum = settings.correct_answer_max




    # ========================================================================
    #      IF THE ANSWER IS CORRECT, SEND MONEY TO THE PROVIDED NUMBER:
    # ========================================================================

    if correct_answer_minimum <= guess <= correct_answer_maximum:
        response = requests.post(
            'https://api.wave.com/v1/payout',
            headers = {
                "authorization": f"Bearer {api_key}",
                "idempotency-key": mobile_number,
            },
            json = {
                "mobile": mobile_number,
                "name": recipient_name,
                "receive_amount": settings.prize_amount,
                "currency": "XOF",
            }
        )

        # ====================================================================



        if response.ok:
            return win(request, background_tasks, name, settings.prize_amount)
        else:
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
            elif err_msg == 'idempotency-mismatch':
                # HACK: we have already sent some money, just pretend it's
                # a win. This way I can test the message queue better.
                return win(request, background_tasks, name, settings.prize_amount)

            return TEMPLATES.TemplateResponse(
                "result.html",
                {"request": request, "txt": err_msg},
            )
    else:
        lose_msg = f"🫥 {name} guessed wrong."
        background_tasks.add_task(post_message, message=lose_msg)
        return TEMPLATES.TemplateResponse(
            "result.html",
            {"request": request, "txt": "wrong answer :("},
        )


@app.get('/stream')
async def message_stream(request: Request):
    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            query = """
                select id, data
                from data
                where not has_been_broadcast
                order by id desc
                limit 100;
            """

            rows = await database.fetch_all(query=query)

            if len(rows) > 0:
                msg_data = "\n".join([
                    f"<div>{data}</div>"
                    for (id, data) in rows
                ])

                yield {
                    "event": "message",
                    # "id": "message_id",
                    # "retry": RETRY_TIMEOUT,
                    "data": msg_data
                }

                # Mark the just broadcast IDs as ack'ed
                query = "update data set has_been_broadcast=true where id = :id"
                new_ids = [{"id": id} for (id, _) in rows]
                await database.execute_many(query=query, values=new_ids)

            await asyncio.sleep(STREAM_DELAY)

    return EventSourceResponse(event_generator())
