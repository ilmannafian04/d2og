from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Download(models.Model):
    key = models.TextField(primary_key=True)


class DownloadUrl(models.Model):
    download = models.ForeignKey(Download, models.CASCADE)
    url = models.URLField()
    idx = models.IntegerField(validators=(MaxValueValidator(9), MinValueValidator(0)), default=0)
    status = models.BooleanField(default=False)
