from django.urls import path
from . import views

urlpatterns = [
    path('check/', views.symptom_checker, name='symptom_checker'),
    path('assistant/', views.health_assistant, name='health_assistant'),
    path('doctor/', views.doctor_chat, name='doctor_chat'),
    path('ocr/', views.prescription_ocr, name='prescription_ocr'),
    path('interaction-network/', views.drug_interaction_api, name='drug_interaction_api'),
    path('check-interactions/', views.check_interactions_ajax, name='check_interactions_ajax'),
]
