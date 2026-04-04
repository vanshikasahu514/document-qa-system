from django.db import models
import uuid


class Document(models.Model):
    """Stores metadata about an uploaded PDF."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    num_chunks = models.IntegerField(default=0)
    num_words = models.IntegerField(default=0)
    num_chars = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_name} ({self.id})"

    class Meta:
        ordering = ['-uploaded_at']
