from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from invoices import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Business Profile
    path('business-profile/', views.business_profile_setup, name='business_profile_setup'),
    
    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    
    # Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/confirmation/', views.invoice_confirmation, name='invoice_confirmation'),
    path('invoices/<int:pk>/pdf/', views.generate_pdf, name='generate_pdf'),
    path('pdf-status/', views.pdf_status, name='pdf_status'),
    path('invoices/<int:pk>/email/', views.email_invoice, name='email_invoice'),
    path('invoices/preview/', views.invoice_live_preview, name='invoice_live_preview'),
    path('clients/<int:pk>/json/', views.client_detail_api, name='client_detail_api'),
    path('businesses/<int:pk>/json/', views.business_detail_api, name='business_detail_api'),
    
    # Ad Tracking
    path('api/track-ad/', views.track_ad_click, name='track_ad_click'),
    path('api/exchange-rate/', views.exchange_rate, name='exchange_rate'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)