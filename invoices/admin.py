from django.contrib import admin
from .models import BusinessProfile, Client, Invoice, InvoiceItem, AdClick

@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'email', 'phone', 'created_at']
    search_fields = ['business_name', 'email']
    list_filter = ['created_at']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email']
    list_filter = ['created_at', 'user']

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client', 'user', 'invoice_date', 'due_date', 'total_amount', 'status', 'created_at']
    search_fields = ['invoice_number', 'client__name']
    list_filter = ['status', 'invoice_date', 'created_at']
    inlines = [InvoiceItemInline]
    readonly_fields = ['invoice_number', 'subtotal', 'tax_amount', 'total_amount']

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'description', 'quantity', 'unit_price', 'line_total']
    search_fields = ['description', 'invoice__invoice_number']

@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ['ad_identifier', 'placement', 'user', 'timestamp', 'target_url']
    search_fields = ['ad_identifier', 'user__username']
    list_filter = ['placement', 'timestamp']
    readonly_fields = ['user', 'session_id', 'timestamp', 'ip_address']