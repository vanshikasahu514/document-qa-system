from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'num_words', 'num_chunks', 'uploaded_at')
    readonly_fields = ('id', 'uploaded_at', 'file_path', 'num_chunks', 'num_words', 'num_chars')
    ordering = ('-uploaded_at',)
