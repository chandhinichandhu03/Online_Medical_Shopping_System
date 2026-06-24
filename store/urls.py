from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicine/<int:pk>/', views.medicine_detail, name='medicine_detail'),
    path('emergency/', views.emergency_services, name='emergency_services'),
    path('about/', views.about_us, name='about'),
    
    # Advanced Features
    path('compare/', views.compare_medicines, name='compare_medicines'),
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/toggle/<int:pk>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('interactions/', views.drug_interactions_network, name='drug_interactions_network'),
    path('subscribe/<int:pk>/', views.subscribe_medicine, name='subscribe_medicine'),
    path('subscriptions/', views.subscriptions_list, name='subscriptions_list'),
    path('api/search/', views.search_autocomplete_api, name='search_autocomplete_api'),
]
