import os
import uuid
import json
from pathlib import Path

from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings

from .models import Document
from .forms import UploadDocumentForm, AskQuestionForm
from .qa_engine import engine


class IndexView(View):
    """Serve the single-page UI."""
    def get(self, request):
        doc_id = request.session.get('doc_id')
        context = {'doc_loaded': False}

        if doc_id:
            try:
                doc = Document.objects.get(id=doc_id)
                context.update({
                    'doc_loaded': True,
                    'doc_id': str(doc.id),
                    'doc_name': doc.original_name,
                    'num_words': doc.num_words,
                    'num_chunks': doc.num_chunks,
                })
            except Document.DoesNotExist:
                request.session.pop('doc_id', None)

        return render(request, 'qa/index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class UploadView(View):
    """Handle PDF upload, extraction, embedding."""
    def post(self, request):
        form = UploadDocumentForm(request.POST, request.FILES)
        if not form.is_valid():
            errors = '; '.join(
                f"{k}: {', '.join(v)}" for k, v in form.errors.items()
            )
            return JsonResponse({'error': errors}, status=400)

        uploaded_file = form.cleaned_data['file']
        doc_id = uuid.uuid4()

        # Save file
        upload_dir = Path(settings.MEDIA_ROOT)
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{doc_id}_{uploaded_file.name.replace(' ', '_')}"
        filepath = upload_dir / safe_name

        with open(filepath, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        try:
            stats = engine.process_document(str(filepath), str(doc_id))
        except ValueError as e:
            filepath.unlink(missing_ok=True)
            return JsonResponse({'error': str(e)}, status=422)
        except Exception as e:
            filepath.unlink(missing_ok=True)
            return JsonResponse({'error': f"Processing failed: {e}"}, status=500)

        # Persist metadata to DB
        doc = Document.objects.create(
            id=doc_id,
            original_name=uploaded_file.name,
            file_path=str(filepath),
            num_chunks=stats['num_chunks'],
            num_words=stats['num_words'],
            num_chars=stats['num_chars'],
        )

        request.session['doc_id'] = str(doc_id)

        return JsonResponse({
            'success': True,
            'doc_id': str(doc_id),
            'filename': uploaded_file.name,
            'num_words': stats['num_words'],
            'num_chunks': stats['num_chunks'],
            'message': f'"{uploaded_file.name}" processed successfully!',
        })


@method_decorator(csrf_exempt, name='dispatch')
class AskView(View):
    """Handle a question and return an answer."""
    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

        form = AskQuestionForm(body)
        if not form.is_valid():
            errors = '; '.join(
                f"{k}: {', '.join(v)}" for k, v in form.errors.items()
            )
            return JsonResponse({'error': errors}, status=400)

        question = form.cleaned_data['question']
        doc_id = str(form.cleaned_data['doc_id'])

        # Ensure document is in memory; reload from disk if needed
        if not engine.is_loaded(doc_id):
            try:
                doc = Document.objects.get(id=doc_id)
            except Document.DoesNotExist:
                return JsonResponse({'error': 'Document not found. Please re-upload.'}, status=404)

            if not os.path.exists(doc.file_path):
                return JsonResponse({'error': 'File missing on server. Please re-upload.'}, status=404)

            try:
                engine.process_document(doc.file_path, doc_id)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        try:
            result = engine.answer(doc_id, question)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        return JsonResponse({**result, 'question': question})


class DocumentInfoView(View):
    """Return metadata about the currently loaded document."""
    def get(self, request):
        doc_id = request.session.get('doc_id')
        if not doc_id:
            return JsonResponse({'loaded': False})
        try:
            doc = Document.objects.get(id=doc_id)
            return JsonResponse({
                'loaded': True,
                'doc_id': str(doc.id),
                'filename': doc.original_name,
                'num_chunks': doc.num_chunks,
                'num_words': doc.num_words,
                'num_chars': doc.num_chars,
                'uploaded_at': doc.uploaded_at.isoformat(),
            })
        except Document.DoesNotExist:
            return JsonResponse({'loaded': False})
