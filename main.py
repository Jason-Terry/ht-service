import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import resend

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://human-thoughts.blog",
        "http://localhost:4321",
    ],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

resend.api_key = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO = os.environ.get("CONTACT_TO", "jasonalanterry+ht@outlook.com")
FROM_ADDRESS = os.environ.get("FROM_ADDRESS", "contact@human-thoughts.blog")
TURNSTILE_SECRET = os.environ.get("TURNSTILE_SECRET", "")


class ContactForm(BaseModel):
    name: str = Field(max_length=100)
    email: EmailStr
    message: str = Field(max_length=5000)
    turnstile_token: str = Field(alias="cf-turnstile-response")


async def verify_turnstile(token: str) -> bool:
    if not TURNSTILE_SECRET:
        return True  # skip verification if not configured (local dev)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET, "response": token},
        )
        result = resp.json()
        return result.get("success", False)


@app.post("/contact")
@limiter.limit("5/minute")
async def send_contact(form: ContactForm, request: Request):
    if not await verify_turnstile(form.turnstile_token):
        raise HTTPException(status_code=403, detail="Captcha verification failed")

    if not resend.api_key:
        raise HTTPException(status_code=500, detail="Mail service not configured")

    try:
        resend.Emails.send({
            "from": f"{form.name} via Human Thoughts <{FROM_ADDRESS}>",
            "to": [CONTACT_TO],
            "reply_to": form.email,
            "subject": f"[Human Thoughts] Message from {form.name}",
            "text": f"Name: {form.name}\nEmail: {form.email}\n\n{form.message}",
        })
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send message")

    return {"status": "sent"}


@app.get("/health")
async def health():
    return {"status": "ok"}
