import signal
import sys

import pika


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)


connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        '152.118.148.95',
        5672,
        '/0806444524',
        pika.PlainCredentials('0806444524', '0806444524')
    )
)
channel = connection.channel()
channel.exchange_declare(exchange='1706067626T', exchange_type='topic')
queue = channel.queue_declare(queue='progress.time')
channel.queue_bind(exchange='1706067626T', queue=queue.method.queue)
channel.basic_consume(queue='progress.time',
                      auto_ack=True,
                      on_message_callback=callback)
print(' [*] Waiting for messages. To exit press CTRL+C')


def signal_handler(signal, frame):
    connection.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
channel.start_consuming()
