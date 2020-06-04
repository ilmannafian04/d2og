import json
import os

import pika
from dotenv import load_dotenv

load_dotenv()
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        os.environ.get('RMQ_HOST'),
        int(os.environ.get('RMQ_PORT', 5672)),
        os.environ.get('RMQ_VHOST'),
        pika.PlainCredentials(os.environ.get('RMQ_USER'), os.environ.get('RMQ_PASS'))
    )
)
global_channel = connection.channel()
exchange_name = f'{os.environ.get("NPM")}D'
global_channel.exchange_declare(exchange_name, 'direct')
queue = global_channel.queue_declare(queue='download')
global_channel.queue_bind(exchange=exchange_name, queue=queue.method.queue)


def download_handler(channel, method_frame, header_frame, body):
    message = body.decode('utf-8')
    message = json.loads(message)
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    print(message)


global_channel.basic_consume('download', download_handler)
try:
    global_channel.start_consuming()
except KeyboardInterrupt:
    global_channel.stop_consuming()
connection.close()
