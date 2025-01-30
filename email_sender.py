# app/email_sender.py

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from fastapi import HTTPException

conf = ConnectionConfig(
    MAIL_USERNAME="Username",
    MAIL_PASSWORD="Password",
    MAIL_SERVER="smtp.google.com",
    MAIL_PORT=587,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    MAIL_FROM="someEmail@example.com"
)


async def send_email(recipient: EmailStr, subject: str, body: str):
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[recipient],
            body=body,
            subtype="html"
        )

        fm = FastMail(conf)
        await fm.send_message(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
