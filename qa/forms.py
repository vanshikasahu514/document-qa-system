from django import forms


class UploadDocumentForm(forms.Form):
    file = forms.FileField(
        label='PDF Document',
        help_text='Upload a PDF file (max 16 MB)',
    )

    def clean_file(self):
        f = self.cleaned_data['file']
        if not f.name.lower().endswith('.pdf'):
            raise forms.ValidationError("Only PDF files are allowed.")
        if f.size > 16 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 16 MB.")
        return f


class AskQuestionForm(forms.Form):
    question = forms.CharField(
        max_length=500,
        strip=True,
    )
    doc_id = forms.UUIDField()
