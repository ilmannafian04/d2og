import uuid

from django.http import HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render, redirect

from producer.models import Download, DownloadUrl


def index(request):
    if request.method == 'GET':
        return render(request, 'index.html')
    elif request.method == 'POST':
        if 'urls' in request.POST:
            routing_key = uuid.uuid4()
            download = Download(key=routing_key)
            download.save()
            for url in request.POST.getlist('urls'):
                url_entity = DownloadUrl(download=download, url=url)
                url_entity.save()
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
