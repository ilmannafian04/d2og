import json
import os
import types
import zipfile
from functools import partial

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
    folder_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media',
                                    message['key'])
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    folder_size = sum(
        os.path.getsize(os.path.join(folder_directory, f)) for f in os.listdir(folder_directory) if
        os.path.isfile(os.path.join(folder_directory, f)))
    if len([i for i in os.listdir(folder_directory) if os.path.isfile(os.path.join(folder_directory, i))]) == 10:
        zip_name = f'{message["key"]}.zip'
        compress_queue = channel.queue_declare(queue=f'{message["key"]}.compress')
        channel.queue_bind(exchange=exchange_name, queue=compress_queue.method.queue)

        def progress(total_size, original_write, _, buf):
            progress.bytes += len(buf)
            percentage = round(progress.bytes * 100 / total_size, 2)
            channel.basic_publish(
                exchange_name,
                f'{message["key"]}.compress',
                json.dumps(
                    {
                        'key': message['key'],
                        'progress': percentage if percentage <= 100 else 100.0
                    },
                    separators=(',', ':')
                )
            )
            return original_write(buf)

        progress.bytes = 0
        with zipfile.ZipFile(os.path.join(folder_directory, zip_name), 'w') as _zip:
            _zip.fp.write = types.MethodType(partial(progress, folder_size, _zip.fp.write), _zip.fp)
            for filename in os.listdir(folder_directory):
                if filename != zip_name:
                    _zip.write(os.path.join(folder_directory, filename), filename)


global_channel.basic_consume('progress.download', compress_handler)
try:
    global_channel.start_consuming()
except KeyboardInterrupt:
    global_channel.stop_consuming()
connection.close()
