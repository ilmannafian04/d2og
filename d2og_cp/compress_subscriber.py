import base64
import calendar
import datetime
import errno
import hashlib
import json
import os
import types
import zipfile
from functools import partial

import pika
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '..', '.env'))
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        os.environ.get('RMQ_HOST'),
        int(os.environ.get('RMQ_PORT', 5672)),
        os.environ.get('RMQ_VHOST'),
        pika.PlainCredentials(os.environ.get('RMQ_USER'), os.environ.get('RMQ_PASS'))
    )
)
global_channel = connection.channel()
exchange_name = f'{os.environ.get("NPM")}_TOPIC'
global_channel.exchange_declare(exchange_name, 'topic')
queue = global_channel.queue_declare('progress.download')
global_channel.queue_bind(exchange=exchange_name, queue=queue.method.queue)


def compress_handler(channel, method_frame, _, body):
    message = json.loads(body.decode('utf-8'))
    media_folder = os.path.join(BASE_DIR, '..', 'media')
    source_folder = os.path.join(media_folder, message['key'])
    compressed_folder = os.path.join(media_folder, 'compressed')
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    folder_size = sum(
        os.path.getsize(os.path.join(source_folder, f)) for f in os.listdir(source_folder) if
        os.path.isfile(os.path.join(source_folder, f)))
    if len([i for i in os.listdir(source_folder) if os.path.isfile(os.path.join(source_folder, i))]) == 10:
        if not os.path.exists(compressed_folder):
            try:
                os.makedirs(compressed_folder)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
        zip_name = f'{message["key"]}.zip'
        compress_queue = channel.queue_declare(queue=f'{message["key"]}.compress', auto_delete=True)
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
        with zipfile.ZipFile(os.path.join(compressed_folder, zip_name), 'w') as _zip:
            _zip.fp.write = types.MethodType(partial(progress, folder_size, _zip.fp.write), _zip.fp)
            for filename in os.listdir(source_folder):
                if filename != zip_name:
                    _zip.write(os.path.join(source_folder, filename), filename)
        url_queue = channel.queue_declare(queue=f'{message["key"]}.secret', auto_delete=True)
        channel.queue_bind(exchange=exchange_name, queue=url_queue.method.queue)
        url = f'/{zip_name}'
        future = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        expiry = calendar.timegm(future.timetuple())
        secure_link = f'{url} {os.environ.get("NGINX_SECRET_KEY")} {expiry}'.encode('utf-8')
        link_hash = hashlib.md5(secure_link).digest()
        base64_hash = base64.urlsafe_b64encode(link_hash)
        channel.basic_publish(
            exchange_name,
            f'{message["key"]}.secret',
            json.dumps(
                {
                    'key': message['key'],
                    'fileName': zip_name,
                    'md5': base64_hash.decode('utf-8').rstrip('='),
                    'expires': expiry
                },
                separators=(',', ':')
            )
        )


global_channel.basic_consume('progress.download', compress_handler)
try:
    global_channel.start_consuming()
except KeyboardInterrupt:
    global_channel.stop_consuming()
connection.close()
