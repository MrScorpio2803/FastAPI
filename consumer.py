# app/consumer.py

import pika
import json
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
import asyncio
from email_sender import send_email  # Импортируем функцию для отправки email


# Настройки RabbitMQ
def get_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    return connection


def on_license_expiration(ch, method, properties, body):
    license_info = json.loads(body)
    client_email = license_info['email']
    subject = "License Expiration Notice"
    body = f"Dear Client, your license with ID {license_info['license_id']} is about to expire on {license_info['expiry_date']}."

    print(f"Sending email to {client_email}...")
    asyncio.run(send_email(client_email, subject, body))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def consume_license_expiration():
    connection = get_connection()
    channel = connection.channel()

    # Объявляем очередь
    channel.queue_declare(queue='license_expiration')

    # Подписываемся на очередь и начинаем получать сообщения
    channel.basic_consume(queue='license_expiration', on_message_callback=on_license_expiration)
    print('Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


if __name__ == "__main__":
    consume_license_expiration()
