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
exchange_name = f'{os.environ.get("NPM")}T'
global_channel.exchange_declare(exchange_name, 'topic')
queue = global_channel.queue_declare('progress.download')
global_channel.queue_bind(exchange=exchange_name, queue=queue.method.queue)


def compress_handler(channel, method_frame, _, body):
    message = json.loads(body.decode('utf-8'))
    folder_directory = os.path.join(os.curdir, '..', 'media', message['key'])
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    if len([i for i in os.listdir(folder_directory) if os.path.isfile(os.path.join(folder_directory, i))]) == 10:
        print('exist 10')


global_channel.basic_consume('progress.download', compress_handler)
try:
    global_channel.start_consuming()
except KeyboardInterrupt:
    global_channel.stop_consuming()
connection.close()
