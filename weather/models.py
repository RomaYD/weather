from django.contrib.sessions.models import Session
from django.db import models

class SearchHistory(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    city = models.CharField(max_length=100)
    search_count = models.IntegerField(default=1)
    last_search = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id', 'last_search']),
            models.Index(fields=['city']),
        ]
