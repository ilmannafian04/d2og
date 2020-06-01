import os
import signal
import sys

import pika
import schedule
import time

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
channel = connection.channel()
exchange_name = f'{os.environ.get("NPM")}T'
channel.exchange_declare(exchange_name, 'topic')
queue = channel.queue_declare(queue='progress.time')
channel.queue_bind(exchange=exchange_name, queue=queue.method.queue)


def publish_time():
    channel.basic_publish(exchange_name, 'progress.time', str(time.time()))


def signal_handler(_, __):
    connection.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
schedule.every().second.do(publish_time)
while True:
    schedule.run_pending()
    time.sleep(1)
