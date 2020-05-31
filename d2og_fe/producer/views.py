import uuid

import pika
from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render, redirect

from producer.models import Download, DownloadUrl


def index(request):
    if request.method == 'GET':
        return render(request, 'index.html')
    elif request.method == 'POST':
        if 'urls' in request.POST:
            routing_key = str(uuid.uuid4())
            parameters = pika.ConnectionParameters(
                settings.PUBSUB['RMQ_HOST'],
                settings.PUBSUB['RMQ_PORT'],
                settings.PUBSUB['RMQ_VHOST'],
                pika.PlainCredentials(settings.PUBSUB['RMQ_USER'], settings.PUBSUB['RMQ_PASS'])
            )
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.exchange_declare(exchange=settings.NPM, exchange_type='direct')
            queue = channel.queue_declare(queue=routing_key)
            channel.queue_bind(exchange=settings.NPM, queue=queue.method.queue)
            download = Download(key=routing_key)
            download.save()
            for url in request.POST.getlist('urls'):
                url_entity = DownloadUrl(download=download, url=url)
                url_entity.save()
                channel.basic_publish(exchange=settings.NPM, routing_key=routing_key, body=url)
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