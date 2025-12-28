from django.db import models


class PageView(models.Model):
    path = models.CharField(max_length=225, unique=True)
    count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.path}: {self.count}"
