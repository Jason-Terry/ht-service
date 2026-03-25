import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import resend

app = FastAPI()

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


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    message: str


@app.post("/contact")
async def send_contact(form: ContactForm):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send message")

    return {"status": "sent"}


@app.get("/health")
async def health():
    return {"status": "ok"}
