import json
import uuid

import pika
from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from producer.models import Download, DownloadUrl

parameters = pika.ConnectionParameters(
    settings.PUBSUB['RMQ_HOST'],
    settings.PUBSUB['RMQ_PORT'],
    settings.PUBSUB['RMQ_VHOST'],
    pika.PlainCredentials(settings.PUBSUB['RMQ_USER'], settings.PUBSUB['RMQ_PASS'])
)
exchange_name = f'{settings.NPM}_DIRECT'
placeholder_link = [
    'https://homepages.cae.wisc.edu/~ece533/images/airplane.png',
    'https://homepages.cae.wisc.edu/~ece533/images/arctichare.png',
    'https://homepages.cae.wisc.edu/~ece533/images/baboon.png',
    'https://homepages.cae.wisc.edu/~ece533/images/barbara.png',
    'https://homepages.cae.wisc.edu/~ece533/images/boat.png',
    'https://homepages.cae.wisc.edu/~ece533/images/cat.png',
    'https://homepages.cae.wisc.edu/~ece533/images/fruits.png',
    'https://homepages.cae.wisc.edu/~ece533/images/frymire.png',
    'https://homepages.cae.wisc.edu/~ece533/images/girl.png',
    'https://homepages.cae.wisc.edu/~ece533/images/lena.png'
]


def index(request):
    if request.method == 'GET':
        return render(request, 'index.html', {'placeholder': placeholder_link})
    elif request.method == 'POST':
        if 'urls' in request.POST:
            routing_key = str(uuid.uuid4())
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.exchange_declare(exchange=exchange_name, exchange_type='direct')
            queue = channel.queue_declare(queue='download')
            channel.queue_bind(exchange=exchange_name, queue=queue.method.queue)
            download = Download(key=routing_key)
            download.save()
            for i, url in enumerate(request.POST.getlist('urls')):
                url_entity = DownloadUrl(download=download, url=url, idx=i)
                url_entity.save()
                channel.basic_publish(
                    exchange=exchange_name,
                    routing_key='download',
                    body=json.dumps({'key': routing_key, 'url': url, 'index': i}, separators=(',', ':'))
                )
            connection.close()
            return redirect('progress', key=routing_key)
        else:
            return HttpResponseBadRequest()
    else:
        return HttpResponseNotFound()


def progress(request, key):
    if request.method == 'GET':
        try:
            download = Download.objects.get(key=key)
        except Download.DoesNotExist:
            return HttpResponseNotFound()
        urls = DownloadUrl.objects.filter(download=download)
        context = {'routing_key': key, 'urls': urls}
        return render(request, 'progress.html', context)
    else:
        return HttpResponseNotFound()


@csrf_exempt
def download_progress(request, key, idx):
    try:
        download = Download.objects.get(key=key)
    except Download.DoesNotExist:
        return HttpResponseNotFound()
    if request.method == 'POST':
        try:
            url = DownloadUrl.objects.get(idx=idx, download=download)
        except DownloadUrl.DoesNotExist:
            return HttpResponseNotFound()
        url.status = True
        url.save()
        urls = DownloadUrl.objects.filter(download=download, status=True)
        if len(urls) == 10:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.exchange_declare(f'{settings.NPM}_TOPIC', exchange_type='topic')
            ipc_queue = channel.queue_declare(queue='progress.download')
            channel.queue_bind(exchange=f'{settings.NPM}_TOPIC', queue=ipc_queue.method.queue)
            channel.basic_publish(
                f'{settings.NPM}_TOPIC',
                'progress.download',
                json.dumps({'key': key}, separators=(',', ':'))
            )
            connection.close()
        return JsonResponse({'success': True})
    else:
        return HttpResponseNotFound()
