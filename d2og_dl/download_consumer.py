import errno
import json
import os
import re
import urllib.parse

import pika
import requests
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
npm = os.environ.get("NPM")
global_channel.exchange_declare(f'{npm}D', 'direct')
queue = global_channel.queue_declare(queue='download')
global_channel.queue_bind(exchange=f'{npm}D', queue=queue.method.queue)
global_channel.exchange_declare(f'{npm}T', 'topic')
ipc_queue = global_channel.queue_declare(queue='progress.download')
global_channel.queue_bind(exchange=f'{npm}T', queue=ipc_queue.method.queue)


def get_filename(url, content_disposition):
    if content_disposition is None:
        if len(url.split('/')[-1]) > 0:
            return url.split('/')[-1]
        else:
            return urllib.parse.quote(url, '')
    fname = re.findall('filename=(.+)', content_disposition)
    if len(fname) == 0:
        return None
    return fname[0]


def download_handler(channel, method_frame, _, body):
    message = body.decode('utf-8')
    message = json.loads(message)
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    response = requests.get(message['url'], stream=True)
    filename = get_filename(message['url'], response.headers.get('content-disposition'))
    download_folder = os.path.join(os.curdir, '..', 'media', message['key'])
    if not os.path.exists(download_folder):
        try:
            os.makedirs(download_folder)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    elif os.path.exists(os.path.join(download_folder, filename)):
        filename = f'{message["index"]}-{get_filename(message["url"], response.headers.get("content-disposition"))}'
    download_queue = channel.queue_declare(queue=f'{message["key"]}.download')
    channel.queue_bind(exchange=f'{npm}T', queue=download_queue.method.queue)
    with open(os.path.join(download_folder, filename), "wb") as file:
        filesize = response.headers.get('content-length')
        if filesize is None:
            file.write(response.content)
            channel.basic_publish(
                f'{npm}T',
                f'{message["key"]}.download',
                json.dumps(
                    {
                        'key': message['key'],
                        'index': message['index'],
                        'progress': 100.0
                    },
                    separators=(',', ':')
                )
            )
        else:
            downloaded = 0
            filesize = int(filesize)
            for data in response.iter_content(chunk_size=filesize // 100):
                downloaded += len(data)
                file.write(data)
                channel.basic_publish(
                    f'{npm}T',
                    f'{message["key"]}.download',
                    json.dumps(
                        {
                            'key': message['key'],
                            'index': message['index'],
                            'progress': round(downloaded * 100 / filesize, 2)
                        },
                        separators=(',', ':')
                    )
                )
        channel.basic_publish(
            f'{npm}T',
            'progress.download',
            json.dumps({'key': message['key']}, separators=(',', ':'))
        )


global_channel.basic_consume('download', download_handler)
try:
    global_channel.start_consuming()
except KeyboardInterrupt:
    global_channel.stop_consuming()
connection.close()
