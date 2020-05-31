from django.db import models


class Download(models.Model):
    key = models.TextField(primary_key=True)


class DownloadUrl(models.Model):
    download = models.ForeignKey(Download, models.CASCADE)
    url = models.URLField()
