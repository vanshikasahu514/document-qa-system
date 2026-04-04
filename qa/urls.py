from django.urls import path
from .views import IndexView, UploadView, AskView, DocumentInfoView

app_name = 'qa'

urlpatterns = [
    path('',             IndexView.as_view(),      name='index'),
    path('upload/',      UploadView.as_view(),     name='upload'),
    path('ask/',         AskView.as_view(),         name='ask'),
    path('doc-info/',    DocumentInfoView.as_view(), name='doc_info'),
]
