from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType

from src.config import settings
from src.schemas import MailSchema


def send_mail_background(
    background_tasks: BackgroundTasks,
    message: MailSchema,
) -> None:
    messages = MessageSchema(
        subject=message.subject,
        recipients=message.recipients,
        body=message.body,
        subtype=MessageType.plain,
    )
    fm = FastMail(settings.config_for_fastapi_mail)
    background_tasks.add_task(fm.send_message, messages, None)
