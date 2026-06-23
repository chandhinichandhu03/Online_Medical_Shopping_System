from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Advanced Account Features
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('family/add/', views.family_add, name='family_add'),
    path('family/delete/<int:pk>/', views.family_delete, name='family_delete'),
    path('reminders/add/', views.reminder_add, name='reminder_add'),
    path('reminders/delete/<int:pk>/', views.reminder_delete, name='reminder_delete'),
    path('reminders/log/<int:pk>/', views.reminder_log, name='reminder_log'),
    
    # MFA
    path('mfa/', views.mfa_verification, name='mfa_verification'),
    path('mfa/toggle/', views.mfa_toggle, name='mfa_toggle'),
]
