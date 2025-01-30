# app/publisher.py

import pika
import json


# Устанавливаем соединение с RabbitMQ
def get_connection():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    return connection


def send_license_expiration_notification(license_info):
    connection = get_connection()
    channel = connection.channel()

    channel.queue_declare(queue='license_expiration')
    license_info['expiry_date'] = license_info['expiry_date'].isoformat()
    message = json.dumps(license_info)
    channel.basic_publish(exchange='',
                          routing_key='license_expiration',
                          body=message)

    print(f"Sent message: {message}")
    connection.close()
