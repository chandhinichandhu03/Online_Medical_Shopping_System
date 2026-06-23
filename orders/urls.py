from django.urls import path
from . import views

urlpatterns = [
    path('add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('history/', views.order_history, name='order_history'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Advanced Logistics & Orders
    path('pharmacist/queue/', views.pharmacist_queue, name='pharmacist_queue'),
    path('pharmacist/validate/<int:pk>/<str:action>/', views.pharmacist_validate, name='pharmacist_validate'),
    path('blockchain/', views.blockchain_ledger, name='blockchain_ledger'),
    path('tracking/<int:pk>/', views.order_tracking, name='order_tracking'),
]
