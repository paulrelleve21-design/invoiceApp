import json
import shutil
import subprocess
import tempfile
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import render_to_string
from django.urls import reverse
import shutil
import subprocess
import tempfile
import os


from .models import BusinessProfile, Client, Invoice, InvoiceItem, AdClick
from django.http import JsonResponse
from django.db.models import Sum, Count
from decimal import Decimal
from .forms import BusinessProfileForm, ClientForm, InvoiceForm, InvoiceItemFormSet
from datetime import date


def login_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard')

	if request.method == 'POST':
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			user = form.get_user()
			login(request, user)
			messages.success(request, 'Logged in successfully.')
			return redirect('dashboard')
		messages.error(request, 'Invalid username or password.')
	else:
		form = AuthenticationForm(request)
	return render(request, 'registration/login.html', {'form': form})


def register_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard')

	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			messages.success(request, 'Registration successful. You are now logged in.')
			return redirect('dashboard')
		messages.error(request, 'Please correct the errors below.')
	else:
		form = UserCreationForm()
	return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
	logout(request)
	messages.info(request, 'You have been logged out.')
	return redirect('login')


@login_required
def dashboard_view(request):
	# Determine invoices in scope (superuser sees all)
	if request.user.is_superuser:
		invoices_qs = Invoice.objects.all()
		clients_qs = Client.objects.all()
	else:
		invoices_qs = Invoice.objects.filter(user=request.user)
		clients_qs = Client.objects.filter(user=request.user)

	totals = invoices_qs.aggregate(total_revenue=Sum('total_amount'))
	total_revenue = totals.get('total_revenue') or Decimal('0.00')
	total_invoices = invoices_qs.count()
	paid_count = invoices_qs.filter(status='paid').count()
	overdue_count = invoices_qs.filter(status='overdue').count()
	pending_count = invoices_qs.exclude(status='paid').count()

	recent_invoices = invoices_qs.order_by('-created_at')[:5]

	# Top clients by invoiced amount
	top_clients = clients_qs.annotate(invoices_count=Count('invoices'), total_invoiced=Sum('invoices__total_amount')).order_by('-total_invoiced')[:5]

	context = {
		'total_revenue': total_revenue,
		'total_invoices': total_invoices,
		'paid_count': paid_count,
		'overdue_count': overdue_count,
		'pending_count': pending_count,
		'recent_invoices': recent_invoices,
		'top_clients': top_clients,
	}
	return render(request, 'dashboard.html', context)


@login_required
def business_profile_setup(request):
	# Support multiple BusinessProfiles per user: list, create, edit, delete
	businesses = BusinessProfile.objects.filter(user=request.user).order_by('-created_at')

	# Delete flow: simple POST with delete_business_pk from template
	if request.method == 'POST' and request.POST.get('delete_business_pk'):
		try:
			pk = int(request.POST.get('delete_business_pk'))
			bp = BusinessProfile.objects.get(pk=pk, user=request.user)
			bp.delete()
			messages.success(request, 'Business profile deleted.')
		except Exception:
			messages.error(request, 'Failed to delete business profile.')
		return redirect('business_profile_setup')

	# Edit or create
	edit_id = request.GET.get('id') or request.POST.get('id')
	instance = None
	if edit_id:
		try:
			instance = BusinessProfile.objects.get(pk=int(edit_id), user=request.user)
		except Exception:
			instance = None

	if request.method == 'POST' and not request.POST.get('delete_business_pk'):
		form = BusinessProfileForm(request.POST, request.FILES, instance=instance)
		if form.is_valid():
			bp = form.save(commit=False)
			bp.user = request.user
			bp.save()
			messages.success(request, 'Business profile saved.')
			return redirect('business_profile_setup')
		else:
			messages.error(request, 'Please correct the errors below.')
	else:
		form = BusinessProfileForm(instance=instance)

	return render(request, 'invoices/business_profile_form.html', {'form': form, 'businesses': businesses})


@login_required
def client_list(request):
	# Superusers see all clients; regular users see only their own
	if request.user.is_superuser:
		clients_qs = Client.objects.all()
	else:
		clients_qs = Client.objects.filter(user=request.user)

	# filtering / search
	q = request.GET.get('q', '').strip()
	if q:
		clients_qs = clients_qs.filter(name__icontains=q) | clients_qs.filter(email__icontains=q)

	# Annotate with invoice counts and total invoiced amount
	clients = clients_qs.annotate(
		invoices_count=Count('invoices'),
		total_invoiced=Sum('invoices__total_amount')
	).order_by('-created_at')

	return render(request, 'invoices/client_list.html', {'clients': clients, 'q': q})


@login_required
def client_detail_api(request, pk):
	client = get_object_or_404(Client, pk=pk)
	data = {
		'id': client.pk,
		'name': client.name,
		'email': client.email,
		'phone': client.phone,
		'street': client.street,
		'city': client.city,
		'state': client.state,
		'zip_code': client.zip_code,
		'country': client.country,
		'address': client.address,
	}
	return JsonResponse(data)


@login_required
def business_detail_api(request, pk):
	bp = get_object_or_404(BusinessProfile, pk=pk, user=request.user)
	data = {
		'id': bp.pk,
		'business_name': bp.business_name,
		'email': bp.email,
		'phone': bp.phone,
		'address': bp.address,
		'city': bp.city,
		'state': bp.state,
		'zip_code': bp.zip_code,
		'country': bp.country,
		'logo_url': bp.logo.url if bp.logo else '',
	}
	return JsonResponse(data)


@login_required
def client_create(request):
	if request.method == 'POST':
		form = ClientForm(request.POST)
		if form.is_valid():
			client = form.save(commit=False)
			client.user = request.user
			client.save()
			messages.success(request, 'Client created.')
			return redirect('client_list')
	else:
		form = ClientForm()
	return render(request, 'invoices/client_form.html', {'form': form, 'action': 'Create'})


@login_required
def client_edit(request, pk):
	client = get_object_or_404(Client, pk=pk, user=request.user)
	if request.method == 'POST':
		form = ClientForm(request.POST, instance=client)
		if form.is_valid():
			form.save()
			messages.success(request, 'Client updated.')
			return redirect('client_list')
	else:
		form = ClientForm(instance=client)
	return render(request, 'invoices/client_form.html', {'form': form, 'action': 'Edit'})


@login_required
def client_delete(request, pk):
	client = get_object_or_404(Client, pk=pk, user=request.user)
	if request.method == 'POST':
		client.delete()
		messages.success(request, 'Client deleted.')
		return redirect('client_list')
	return render(request, 'invoices/client_confirm_delete.html', {'client': client})


@login_required
def invoice_list(request):
	# base queryset
	if request.user.is_superuser:
		invoices_qs = Invoice.objects.all()
	else:
		invoices_qs = Invoice.objects.filter(user=request.user)

	# search and status filtering
	q = request.GET.get('q', '').strip()
	status = request.GET.get('status', '').strip()
	if q:
		invoices_qs = invoices_qs.filter(invoice_number__icontains=q) | invoices_qs.filter(client__name__icontains=q)
	if status:
		invoices_qs = invoices_qs.filter(status=status)

	invoices = invoices_qs.order_by('-created_at')
	return render(request, 'invoices/invoice_list.html', {'invoices': invoices, 'q': q, 'status': status})


@login_required
@xframe_options_exempt
def invoice_live_preview(request):
	"""Accept JSON POST with invoice and items and return PDF (if WeasyPrint native libs available) or HTML preview."""
	if request.method != 'POST':
		return JsonResponse({'error': 'POST required'}, status=405)

	data = None
	# Accept JSON requests (primary) or form-encoded POSTs (fallback from hidden form submit)
	ct = (request.content_type or '').lower()
	if 'application/json' in ct:
		try:
			data = json.loads(request.body.decode('utf-8'))
		except Exception:
			return JsonResponse({'error': 'Invalid JSON'}, status=400)
	else:
		# build a simple data dict from form-encoded POST fields; supports common field names
		try:
			pdata = request.POST
			data = {
				'invoice_number': pdata.get('invoice_number') or pdata.get('id_invoice_number'),
				'invoice_date': pdata.get('invoice_date') or pdata.get('id_invoice_date'),
				'due_date': pdata.get('due_date') or pdata.get('id_due_date'),
				'tax_rate': pdata.get('tax_rate') or pdata.get('id_tax_rate'),
				'discount_amount': pdata.get('discount_amount') or pdata.get('id_discount_amount'),
				'status': pdata.get('status') or pdata.get('id_status'),
				'payment_terms': pdata.get('payment_terms') or pdata.get('id_payment_terms'),
				'notes': pdata.get('notes') or pdata.get('id_notes'),
				'currency': pdata.get('currency') or pdata.get('id_currency') or 'USD',
				'client': {
					'name': pdata.get('client_name') or pdata.get('id_client_name') or pdata.get('client') or '',
					'email': pdata.get('client_email') or pdata.get('id_client_email') or '',
					'phone': pdata.get('client_phone') or pdata.get('id_client_phone') or '',
					'address': pdata.get('client_address') or pdata.get('id_client_address') or '',
				},
				'business': {
					'id': pdata.get('business') or pdata.get('business_id') or '',
					'business_name': pdata.get('business_name') or pdata.get('id_business_name') or pdata.get('business_name') or pdata.get('id_business_name_text') or '',
					'email': pdata.get('business_email') or pdata.get('id_business_email') or pdata.get('id_business_email_text') or '',
					'phone': pdata.get('business_phone') or pdata.get('id_business_phone') or pdata.get('id_business_phone_text') or '',
					'address': pdata.get('business_address') or pdata.get('id_business_address') or pdata.get('id_business_address_text') or '',
					'photo_data_url': pdata.get('business_photo_data_url') or None,
				},
				'items': []
			}
			# attempt to collect formset-like items (e.g., form-0-description or items-0-description)
			import re
			item_map = {}
			for k in pdata.keys():
				m = re.match(r'.*-(\d+)-(.+)', k)
				if m:
					idx = int(m.group(1))
					field = m.group(2)
					item_map.setdefault(idx, {})[field] = pdata.get(k)
			# also handle names like description-0 or 0-description
			for k in pdata.keys():
				m2 = re.match(r'(?:description|desc|item_description)[-_]?(\d+)', k)
				if m2:
					idx = int(m2.group(1))
					item_map.setdefault(idx, {})['description'] = pdata.get(k)
			# convert to list
			for idx in sorted(item_map.keys()):
				itm = item_map[idx]
				try:
					qty = float(itm.get('quantity') or itm.get('qty') or 0)
				except Exception:
					qty = 0
				try:
					unit = float(itm.get('unit_price') or itm.get('price') or 0)
				except Exception:
					unit = 0
				data['items'].append({'description': itm.get('description') or itm.get('desc') or '', 'quantity': qty, 'unit_price': unit})
		except Exception:
			data = {}

	# Build lightweight objects for template rendering
	from types import SimpleNamespace

	client_data = data.get('client') or {}
	client_obj = SimpleNamespace(
		name=client_data.get('name') or client_data.get('display') or 'Client',
		email=client_data.get('email', ''),
		phone=client_data.get('phone', ''),
		address=client_data.get('address', '')
	)

	items = []
	for it in data.get('items', []):
		items.append(SimpleNamespace(description=it.get('description', ''), quantity=it.get('quantity', 0), unit_price=it.get('unit_price', 0), line_total=(float(it.get('quantity', 0)) * float(it.get('unit_price', 0)))))

	class ItemList:
		def __init__(self, items):
			self._items = items
		def all(self):
			return self._items
		def exists(self):
			return bool(self._items)

	subtotal = sum([i.line_total for i in items])
	tax_rate = float(data.get('tax_rate') or 0)
	tax_amount = subtotal * (tax_rate / 100.0)
	discount = float(data.get('discount_amount') or 0)
	total = subtotal + tax_amount - discount

	invoice_obj = SimpleNamespace(
		invoice_number=data.get('invoice_number', 'PREVIEW'),
		invoice_date=data.get('invoice_date', ''),
		due_date=data.get('due_date', ''),
		status=data.get('status', 'draft'),
		# For Django templates that expect a model-like API (invoice.get_status_display),
		# provide a simple attribute so templates can render the status label when
		# previewing via JSON payloads. Capitalize the first letter for readability.
		get_status_display=str(data.get('status', 'draft') or '').capitalize(),
		client=client_obj,
		client_name=client_data.get('name') or None,
		client_email=client_data.get('email') or None,
		client_phone=client_data.get('phone') or None,
		client_address=client_data.get('address') or None,
		items=ItemList(items),
		subtotal=subtotal,
		tax_rate=tax_rate,
		tax_amount=tax_amount,
		discount_amount=discount,
		total_amount=total,
		currency=data.get('currency', 'USD'),
		payment_terms=data.get('payment_terms', ''),
		notes=data.get('notes', ''),
	)

	# If client posted business snapshot data (editable fields or uploaded image), prefer that
	bdata = data.get('business') or {}
	if bdata:
		from types import SimpleNamespace
		biz_logo = None
		# If client posted an uploaded image (data URL), use it
		if bdata.get('photo_data_url'):
			biz_logo = SimpleNamespace(url=bdata.get('photo_data_url'))
		# If no uploaded photo but a business id was provided, try to load stored logo
		elif bdata.get('id'):
			try:
				bp_id = int(bdata.get('id'))
				bp_obj = BusinessProfile.objects.filter(pk=bp_id, user=request.user).first()
				if bp_obj and getattr(bp_obj, 'logo', None):
					u = bp_obj.logo.url
					if u and not u.startswith('data:') and not u.startswith('http'):
						u = request.build_absolute_uri(u)
					biz_logo = SimpleNamespace(url=u)
			except Exception:
				biz_logo = None
		business = SimpleNamespace(
			business_name=bdata.get('business_name') or bdata.get('name') or '',
			email=bdata.get('email') or '',
			phone=bdata.get('phone') or '',
			address=bdata.get('address') or '',
			city=bdata.get('city') or '',
			state=bdata.get('state') or '',
			zip_code=bdata.get('zip_code') or '',
			country=bdata.get('country') or '',
			logo=biz_logo,
		)
	else:
		# If no posted business snapshot, prefer the first BusinessProfile for this user
		bp = BusinessProfile.objects.filter(user=request.user).first()
		if bp:
			# Build a lightweight object so templates can access .logo.url
			from types import SimpleNamespace as _SN
			biz_logo = None
			try:
				if bp.logo:
					# ensure an absolute URL so iframe/srcdoc previews can load the image
					u = bp.logo.url
					if u and not u.startswith('data:') and not u.startswith('http'):
						u = request.build_absolute_uri(u)
					biz_logo = _SN(url=u)
			except Exception:
				biz_logo = None
			business = _SN(
				business_name=getattr(bp, 'business_name', ''),
				email=getattr(bp, 'email', ''),
				phone=getattr(bp, 'phone', ''),
				address=getattr(bp, 'address', ''),
				city=getattr(bp, 'city', ''),
				state=getattr(bp, 'state', ''),
				zip_code=getattr(bp, 'zip_code', ''),
				country=getattr(bp, 'country', ''),
				logo=biz_logo,
			)
		else:
			business = None

	html_string = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice_obj, 'business': business}, request=request)

	# Try to render PDF
	try:
		from weasyprint import HTML
	except Exception:
		# If a PDF download was explicitly requested, still return the HTML but include a helpful status/message.
		# The client-side will handle non-PDF responses gracefully.
		return HttpResponse(html_string, content_type='text/html')

	try:
		html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
		pdf = html.write_pdf()
		response = HttpResponse(pdf, content_type='application/pdf')
		# If client requested a direct download (e.g., ?format=pdf) send as attachment, otherwise inline preview
		if request.GET.get('format') == 'pdf':
			response['Content-Disposition'] = 'attachment; filename="invoice_preview.pdf"'
		else:
			response['Content-Disposition'] = 'inline; filename="invoice_preview.pdf"'
		return response
	except Exception:
		return HttpResponse(html_string, content_type='text/html')


@login_required
def invoice_create(request):
	if request.method == 'POST':
		# If the user typed a new client name instead of selecting an existing client,
		# create that Client first so the InvoiceForm (which requires `client` FK)
		# can validate correctly.
		post_data = request.POST.copy()
		client_field = post_data.get('client') or ''
		new_client_name = post_data.get('id_client_create') or ''
		if (not client_field) and new_client_name:
			# create lightweight client record
			client = Client.objects.create(
				user=request.user,
				name=new_client_name,
				email=post_data.get('client_email') or post_data.get('id_client_email') or '',
				phone=post_data.get('client_phone') or post_data.get('id_client_phone') or '',
				address=post_data.get('client_address') or post_data.get('id_client_address') or ''
			)
			post_data['client'] = str(client.pk)

		# include uploaded files so file inputs (business photo etc.) are processed
		form = InvoiceForm(post_data, request.FILES, user=request.user)
		# create a bound formset (include files) so uploaded file fields in formset are handled
		formset = InvoiceItemFormSet(request.POST, request.FILES)

		if form.is_valid():
			invoice = form.save(commit=False)
			invoice.user = request.user

			# Read any business fields submitted so we can populate the invoice snapshot
			biz_id = post_data.get('business_id') or post_data.get('business') or ''
			biz_name = post_data.get('business_name') or post_data.get('id_business_name_text') or ''
			biz_email = post_data.get('business_email') or post_data.get('id_business_email_text') or ''
			biz_phone = post_data.get('business_phone') or post_data.get('id_business_phone_text') or ''
			biz_addr = post_data.get('business_address') or post_data.get('id_business_address_text') or ''

			# populate business snapshot fields on the invoice so the PDF/preview
			# remains the same even if the user's BusinessProfile changes later
			if biz_name:
				invoice.business_name = biz_name
			if biz_email:
				invoice.business_email = biz_email
			if biz_phone:
				invoice.business_phone = biz_phone
			if biz_addr:
				invoice.business_address = biz_addr
			# Business photo upload removed from invoice flow; users should edit
			# their BusinessProfile to update the canonical logo instead.
			# Handle client creation when a new client name was typed instead of selecting existing client
			try:
				client_field = request.POST.get('client') or ''
				new_client_name = request.POST.get('id_client_create') or ''
				if (not client_field) and new_client_name:
					# create lightweight client record and attach
					client = Client.objects.create(
						user=request.user,
						name=new_client_name,
						email=request.POST.get('client_email') or request.POST.get('id_client_email') or '',
						phone=request.POST.get('client_phone') or request.POST.get('id_client_phone') or '',
						address=request.POST.get('client_address') or request.POST.get('id_client_address') or ''
					)
					# attach to invoice if model has a client relation
					try: setattr(invoice, 'client', client)
					except Exception: pass
				elif client_field:
					try:
						cobj = Client.objects.filter(pk=int(client_field), user=request.user).first()
						if cobj:
							try: setattr(invoice, 'client', cobj)
							except Exception: pass
					except Exception:
						pass
			except Exception:
				pass
			
			# Persist or update a BusinessProfile snapshot if provided (and attach to invoice if possible)
			biz_id = request.POST.get('business_id') or request.POST.get('business') or ''
			biz_name = request.POST.get('business_name') or request.POST.get('id_business_name_text') or ''
			biz_email = request.POST.get('business_email') or request.POST.get('id_business_email_text') or ''
			biz_phone = request.POST.get('business_phone') or request.POST.get('id_business_phone_text') or ''
			biz_addr = request.POST.get('business_address') or request.POST.get('id_business_address_text') or ''
			bp_obj = None
			try:
				# Try to resolve an existing business by id first (must belong to user)
				if biz_id:
					try:
						bp_obj = BusinessProfile.objects.filter(pk=int(biz_id), user=request.user).first()
					except Exception:
						bp_obj = None
				# If no matching id, but a name was provided, get or create by name for this user
				if not bp_obj and biz_name:
					bp_obj, created = BusinessProfile.objects.get_or_create(
						user=request.user,
						business_name=biz_name,
						defaults={'email': biz_email or None, 'phone': biz_phone or None, 'address': biz_addr or None}
					)
				# If we have a BusinessProfile instance, update any provided fields and save
				if bp_obj:
					updated = False
					if biz_name and bp_obj.business_name != biz_name:
						bp_obj.business_name = biz_name; updated = True
					if biz_email and bp_obj.email != biz_email:
						bp_obj.email = biz_email; updated = True
					if biz_phone and bp_obj.phone != biz_phone:
						bp_obj.phone = biz_phone; updated = True
					if biz_addr and bp_obj.address != biz_addr:
						bp_obj.address = biz_addr; updated = True
					# Do NOT copy invoice-uploaded business photo into the canonical BusinessProfile here.
					# Invoice-level photo should be invoice-specific only and saved to Invoice.business_logo.
					# Always save if we created the object or if any provided fields changed
					if updated or (bp_obj.pk and not bp_obj.created_at):
						bp_obj.save()
			except Exception:
				# don't let business profile failures block invoice saving
				bp_obj = None

			invoice.save()
			# bind formset to the saved invoice instance and validate/save
			formset = InvoiceItemFormSet(request.POST, request.FILES, instance=invoice)
			if formset.is_valid():
				formset.save()
				invoice.recalc_totals()
				messages.success(request, 'Invoice created.')
				return redirect('invoice_list')
			else:
				# surface formset errors to help debug client-side issues
				msgs = []
				for fs_err in formset.errors:
					if fs_err:
						msgs.append(str(fs_err))
				if msgs:
					messages.error(request, 'Invoice items errors: ' + '; '.join(msgs))
				else:
					messages.error(request, 'Please correct the invoice items.')
		else:
			# show form errors for easier debugging
			err_msgs = []
			for f, errs in form.errors.items():
				err_msgs.append(f + ': ' + '; '.join(errs))
			if err_msgs:
				messages.error(request, 'Form errors: ' + ' | '.join(err_msgs))
			else:
				messages.error(request, 'Please correct the errors below.')
	else:
		# prefill invoice number
		last = Invoice.objects.filter(user=request.user).order_by('-id').first()
		if last:
			try:
				next_num = f"INV-{last.id + 1:05d}"
			except Exception:
				next_num = 'INV-00001'
		else:
			next_num = 'INV-00001'
		# default invoice_date and currency to avoid required-field validation errors when user omits them
		form = InvoiceForm(initial={'invoice_number': next_num, 'invoice_date': date.today(), 'currency': 'USD'}, user=request.user)
		formset = InvoiceItemFormSet()

	businesses = BusinessProfile.objects.filter(user=request.user).order_by('-created_at')
	# Provide empty invoice and business_initial to keep template lookups safe
	empty_invoice = Invoice()
	business_initial = {'id': '', 'name': '', 'email': '', 'phone': '', 'address': '', 'logo_url': ''}
	return render(request, 'invoices/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Create', 'businesses': businesses, 'business_initial': business_initial, 'invoice': empty_invoice})


@login_required
def invoice_detail(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	business = BusinessProfile.objects.filter(user=request.user).first()
	return render(request, 'invoices/invoice_detail.html', {'invoice': invoice, 'business': business})


@login_required
def invoice_edit(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	if request.method == 'POST':
		# allow creating a new client by text input (same behavior as invoice_create)
		post_data = request.POST.copy()
		client_field = post_data.get('client') or ''
		new_client_name = post_data.get('id_client_create') or ''
		if (not client_field) and new_client_name:
			client = Client.objects.create(
				user=request.user,
				name=new_client_name,
				email=post_data.get('client_email') or post_data.get('id_client_email') or '',
				phone=post_data.get('client_phone') or post_data.get('id_client_phone') or '',
				address=post_data.get('client_address') or post_data.get('id_client_address') or ''
			)
			post_data['client'] = str(client.pk)

		# bind forms to the (possibly modified) POST so client selection validates
		form = InvoiceForm(post_data, request.FILES, instance=invoice)
		formset = InvoiceItemFormSet(post_data, request.FILES, instance=invoice)

		if form.is_valid() and formset.is_valid():
			invoice = form.save(commit=False)
			invoice.user = request.user

			# update/create BusinessProfile (do not attach to invoice model)
			biz_id = post_data.get('business_id') or post_data.get('business') or ''
			biz_name = post_data.get('business_name') or post_data.get('id_business_name_text') or ''
			biz_email = post_data.get('business_email') or post_data.get('id_business_email_text') or ''
			biz_phone = post_data.get('business_phone') or post_data.get('id_business_phone_text') or ''
			biz_addr = post_data.get('business_address') or post_data.get('id_business_address_text') or ''
			try:
				if biz_id:
					bp = BusinessProfile.objects.filter(pk=biz_id, user=request.user).first()
					if bp:
						if biz_name: bp.business_name = biz_name
						if biz_email: bp.email = biz_email
						if biz_phone: bp.phone = biz_phone
						if biz_addr: bp.address = biz_addr
						# Do NOT update BusinessProfile.logo from invoice edit uploads.
						bp.save()
				else:
					if biz_name:
						bp, created = BusinessProfile.objects.get_or_create(user=request.user, business_name=biz_name, defaults={'email': biz_email or None, 'phone': biz_phone or None, 'address': biz_addr or None})
						if not created:
							updated = False
							if biz_email and bp.email != biz_email:
								bp.email = biz_email; updated = True
							if biz_phone and bp.phone != biz_phone:
								bp.phone = biz_phone; updated = True
							if biz_addr and bp.address != biz_addr:
								bp.address = biz_addr; updated = True
							# Do NOT update BusinessProfile.logo from invoice edit uploads.
							if updated:
								bp.save()
			except Exception:
				# don't block invoice save on business profile errors
				pass

			# populate business snapshot for edited invoice as well
			if biz_name:
				invoice.business_name = biz_name
			if biz_email:
				invoice.business_email = biz_email
			if biz_phone:
				invoice.business_phone = biz_phone
			if biz_addr:
				invoice.business_address = biz_addr
			# Business photo upload removed from invoice flow; users should edit
			# their BusinessProfile to update the canonical logo instead.

			invoice.save()
			formset.save()
			invoice.recalc_totals()
			messages.success(request, 'Invoice updated.')
			return redirect('invoice_detail', pk=invoice.pk)
		else:
			# surface errors to help debugging
			if not form.is_valid():
				errs = []
				for f, e in form.errors.items():
					errs.append(f + ': ' + '; '.join(e))
				messages.error(request, 'Form errors: ' + ' | '.join(errs))
			if not formset.is_valid():
				msgs = []
				for fe in formset.errors:
					if fe:
						msgs.append(str(fe))
				if msgs:
					messages.error(request, 'Formset errors: ' + '; '.join(msgs))
	else:
		form = InvoiceForm(instance=invoice)
		formset = InvoiceItemFormSet(instance=invoice)
	businesses = BusinessProfile.objects.filter(user=request.user).order_by('-created_at')

	# Prepare initial values for the business fields so editing an invoice preserves values
	business_initial = {'id': '', 'name': '', 'email': '', 'phone': '', 'address': '', 'logo_url': ''}
	if 'post_data' in locals():
		# POST (possibly invalid) - prefer posted values so the user doesn't lose edits
		business_initial['id'] = post_data.get('business_id') or post_data.get('business') or ''
		business_initial['name'] = post_data.get('business_name') or post_data.get('id_business_name_text') or ''
		business_initial['email'] = post_data.get('business_email') or post_data.get('id_business_email_text') or ''
		business_initial['phone'] = post_data.get('business_phone') or post_data.get('id_business_phone_text') or ''
		business_initial['address'] = post_data.get('business_address') or post_data.get('id_business_address_text') or ''
	else:
		# GET - populate from saved invoice snapshot or match an existing BusinessProfile by name
		business_initial['name'] = invoice.business_name or ''
		business_initial['email'] = invoice.business_email or ''
		business_initial['phone'] = invoice.business_phone or ''
		business_initial['address'] = invoice.business_address or ''
		if invoice.business_logo:
			try:
				business_initial['logo_url'] = invoice.business_logo.url
			except Exception:
				business_initial['logo_url'] = ''
		# try to resolve a matching BusinessProfile so the select can default to it
		if business_initial['name']:
			bp = BusinessProfile.objects.filter(user=request.user, business_name=business_initial['name']).first()
			if bp:
				business_initial['id'] = bp.pk
				if bp.logo:
					try:
						business_initial['logo_url'] = bp.logo.url
					except Exception:
						pass

	return render(request, 'invoices/invoice_form.html', {'form': form, 'formset': formset, 'action': 'Edit', 'businesses': businesses, 'business_initial': business_initial, 'invoice': invoice})


@login_required
def invoice_delete(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	if request.method == 'POST':
		invoice.delete()
		messages.success(request, 'Invoice deleted.')
		return redirect('invoice_list')
	return render(request, 'invoices/invoice_confirm_delete.html', {'invoice': invoice})


@login_required
def invoice_confirmation(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	return render(request, 'invoices/invoice_confirmation.html', {'invoice': invoice})


@login_required
def generate_pdf(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	# Prefer invoice-level snapshot/logo when present so each invoice's PDF reflects
	# the selected/uploaded image. Fall back to the user's BusinessProfile otherwise.
	from types import SimpleNamespace
	business = None
	try:
		if getattr(invoice, 'business_name', None) or getattr(invoice, 'business_logo', None):
			biz_logo = None
			try:
				if invoice.business_logo:
					u = invoice.business_logo.url
					if u and not u.startswith('http') and not u.startswith('data:'):
						u = request.build_absolute_uri(u)
					biz_logo = SimpleNamespace(url=u)
			except Exception:
				biz_logo = None
			business = SimpleNamespace(
				business_name=getattr(invoice, 'business_name', '') or '',
				email=getattr(invoice, 'business_email', '') or '',
				phone=getattr(invoice, 'business_phone', '') or '',
				address=getattr(invoice, 'business_address', '') or '',
				logo=biz_logo,
			)
		else:
			bp = BusinessProfile.objects.filter(user=request.user).first()
			if bp:
				try:
					u = bp.logo.url if getattr(bp, 'logo', None) else None
					if u and not u.startswith('http') and not u.startswith('data:'):
						u = request.build_absolute_uri(u)
					biz_logo = SimpleNamespace(url=u) if u else None
				except Exception:
					biz_logo = None
				business = SimpleNamespace(
					business_name=getattr(bp, 'business_name', '') or '',
					email=getattr(bp, 'email', '') or '',
					phone=getattr(bp, 'phone', '') or '',
					address=getattr(bp, 'address', '') or '',
					logo=biz_logo,
				)
			else:
				business = None

	except Exception:
		business = BusinessProfile.objects.filter(user=request.user).first()

	# render with request so template tags that rely on request (static, media) resolve correctly
	html_string = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice, 'business': business}, request=request)

	# Try to import WeasyPrint first.
	weasy_error = None
	try:
		from weasyprint import HTML
	except Exception as e:
		HTML = None
		weasy_error = str(e)

	# If WeasyPrint is available use it.
	if HTML:
		try:
			html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
			pdf = html.write_pdf()
			response = HttpResponse(pdf, content_type='application/pdf')
			if request.GET.get('format') == 'pdf':
				response['Content-Disposition'] = f'attachment; filename="invoice-{invoice.invoice_number}.pdf"'
			else:
				response['Content-Disposition'] = f'inline; filename="invoice-{invoice.invoice_number}.pdf"'
			return response
		except Exception as e:
			weasy_error = (weasy_error or '') + '\n' + str(e)

	# WeasyPrint not available or failed — attempt wkhtmltopdf fallback.
	wk_cmd_setting = getattr(settings, 'WKHTMLTOPDF_CMD', None)
	candidates = []
	if wk_cmd_setting:
		candidates.append(wk_cmd_setting)
	# prefer PATH lookup
	try:
		found = shutil.which('wkhtmltopdf')
		if found:
			candidates.append(found)
	except Exception:
		pass

	# common locations (Windows / Linux)
	candidates.extend([
		r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
		r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
		'/usr/local/bin/wkhtmltopdf',
		'/usr/bin/wkhtmltopdf',
	])

	wk_error = None
	used_cmd = None
	for cmd in candidates:
		if not cmd:
			continue
		# If cmd is an explicit path, check file exists; if it's a name, shutil.which will help
		try:
			if os.path.isfile(cmd) or shutil.which(cmd):
				used_cmd = cmd
				break
		except Exception:
			continue

	if used_cmd:
		try:
			# write HTML to temp file and generate PDF using wkhtmltopdf
			# Ensure resource URLs (media/static) are absolute so wkhtmltopdf can fetch them
			base_url = request.build_absolute_uri('/')
			html_for_wk = html_string.replace('src="/', f'src="{base_url}').replace("src='/", f"src='{base_url}")
			html_for_wk = html_for_wk.replace('href="/', f'href="{base_url}').replace("href='/", f"href='{base_url}")
			html_for_wk = html_for_wk.replace("url('/", f"url('{base_url}").replace('url("/', f'url("{base_url}')

			with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as fh:
				fh.write(html_for_wk.encode('utf-8'))
				fh.flush()
				tmp_html = fh.name
			tmp_pdf = tmp_html + '.pdf'
			# Ensure we enable local file access for complex templates
			proc = subprocess.run([used_cmd, '--enable-local-file-access', tmp_html, tmp_pdf], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
			if proc.returncode == 0 and os.path.exists(tmp_pdf):
				with open(tmp_pdf, 'rb') as f:
					pdf = f.read()
				try:
					os.unlink(tmp_html)
				except Exception:
					pass
				try:
					os.unlink(tmp_pdf)
				except Exception:
					pass
				response = HttpResponse(pdf, content_type='application/pdf')
				if request.GET.get('format') == 'pdf':
					response['Content-Disposition'] = f'attachment; filename="invoice-{invoice.invoice_number}.pdf"'
				else:
					response['Content-Disposition'] = f'inline; filename="invoice-{invoice.invoice_number}.pdf"'
				return response
			else:
				wk_error = proc.stderr.decode('utf-8', errors='replace')
		except Exception as e:
			wk_error = str(e)

	# If we reach here, no PDF backend produced a PDF. Provide informative HTML fallback
	messages_html = ['PDF generation is currently unavailable.']
	if weasy_error:
		messages_html.append('<strong>WeasyPrint error:</strong> ' + str(weasy_error))
	if used_cmd:
		messages_html.append('<strong>Attempted wkhtmltopdf:</strong> ' + str(used_cmd))
	if wk_error:
		messages_html.append('<strong>wkhtmltopdf error:</strong> ' + str(wk_error))
	if not used_cmd:
		messages_html.append('wkhtmltopdf not found on system PATH or common locations.')
	messages_html.append('To enable PDF downloads, install WeasyPrint with its native dependencies OR install wkhtmltopdf and add it to PATH or set <code>WKHTMLTOPDF_CMD</code> in settings.')

	diagnostic = '<br/>'.join(messages_html)
	html_with_diag = f'<div class="alert alert-warning" style="margin:12px;">{diagnostic}</div>' + html_string
	return HttpResponse(html_with_diag, content_type='text/html')
	try:
		html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
		pdf = html.write_pdf()
		response = HttpResponse(pdf, content_type='application/pdf')
		response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
		try:
			# mark as generated and persist only the pdf_generated flag
			invoice.pdf_generated = True
			invoice.save(update_fields=['pdf_generated'])
		except Exception:
			# don't let a secondary save error break PDF delivery
			pass
		return response
	except Exception:
		messages.error(request, 'Failed to generate PDF. Showing HTML preview instead.')
		return HttpResponse(html_string, content_type='text/html')


@login_required
def pdf_status(request):
	"""Diagnostic endpoint: reports availability of WeasyPrint and wkhtmltopdf."""
	status = {'weasyprint': {'available': False, 'version': None, 'error': None}, 'wkhtmltopdf': {'found': False, 'path': None, 'version': None, 'error': None}, 'settings_WKHTMLTOPDF_CMD': getattr(settings, 'WKHTMLTOPDF_CMD', None)}
	try:
		import weasyprint
		status['weasyprint']['available'] = True
		try:
			status['weasyprint']['version'] = getattr(weasyprint, '__version__', str(weasyprint))
		except Exception:
			status['weasyprint']['version'] = 'unknown'
	except Exception as e:
		status['weasyprint']['error'] = str(e)

	try:
		wk_cmd = shutil.which('wkhtmltopdf') or getattr(settings, 'WKHTMLTOPDF_CMD', None)
		if wk_cmd:
			status['wkhtmltopdf']['found'] = True
			status['wkhtmltopdf']['path'] = wk_cmd
			try:
				p = subprocess.run([wk_cmd, '--version'], capture_output=True, text=True, timeout=5)
				status['wkhtmltopdf']['version'] = p.stdout.strip() or p.stderr.strip()
			except Exception as e:
				status['wkhtmltopdf']['error'] = str(e)
	except Exception as e:
		status['wkhtmltopdf']['error'] = str(e)

	return JsonResponse(status)


@csrf_exempt
def track_ad_click(request):
	if request.method == 'POST':
		try:
			data = json.loads(request.body)
		except Exception:
			data = {}
		AdClick.objects.create(
			ad_identifier=data.get('ad_id') or data.get('ad_identifier', 'unknown'),
			placement=data.get('placement', ''),
			target_url=data.get('url') or data.get('target_url', ''),
		)
		return JsonResponse({'status': 'ok'})
	return JsonResponse({'status': 'method not allowed'}, status=405)


def exchange_rate(request):
	"""Proxy to exchangerate.host for a simple rate lookup: ?base=USD&target=EUR"""
	base = request.GET.get('base', 'USD').upper()
	target = request.GET.get('target', 'USD').upper()
	if base == target:
		return JsonResponse({'rate': 1.0})
	# Prefer requests if available, otherwise use urllib to avoid adding strict dependency
	try:
		try:
			import requests
			r = requests.get('https://api.exchangerate.host/latest', params={'base': base, 'symbols': target}, timeout=5)
			r.raise_for_status()
			data = r.json()
		except Exception:
			# fallback to urllib
			from urllib.request import urlopen
			from urllib.parse import urlencode
			url = 'https://api.exchangerate.host/latest?' + urlencode({'base': base, 'symbols': target})
			with urlopen(url, timeout=5) as fh:
				import json as _json
				data = _json.load(fh)

		rate = data.get('rates', {}).get(target)
		if rate is None:
			return JsonResponse({'error': 'rate not found'}, status=404)
		return JsonResponse({'rate': rate})
	except Exception as e:
		return JsonResponse({'error': str(e)}, status=500)


@login_required
def email_invoice(request, pk):
	invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
	client_email = invoice.client_email or invoice.client.email
	if not client_email:
		messages.error(request, 'Client does not have an email address.')
		return redirect('invoice_detail', pk=pk)

	if request.method == 'POST':
		subject = request.POST.get('subject') or f'Invoice {invoice.invoice_number}'
		message = request.POST.get('message') or 'Please find your invoice attached.'
		from django.core.mail import EmailMessage
		from django.conf import settings

		attachments = []
		# Try to generate PDF; if not possible attach HTML
		html_string = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice, 'business': BusinessProfile.objects.filter(user=request.user).first()})
		try:
			from weasyprint import HTML
			html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
			pdf = html.write_pdf()
			attachments.append((f'invoice_{invoice.invoice_number}.pdf', pdf, 'application/pdf'))
		except Exception:
			# fallback to HTML attachment
			attachments.append((f'invoice_{invoice.invoice_number}.html', html_string.encode('utf-8'), 'text/html'))

		email = EmailMessage(subject=subject, body=message, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None), to=[client_email])
		for name, content, mimetype in attachments:
			email.attach(name, content, mimetype)

		try:
			email.send()
			messages.success(request, 'Invoice emailed to client.')
		except Exception as e:
			messages.error(request, f'Failed to send email: {e}')

		return redirect('invoice_detail', pk=pk)

	# GET -> show simple send form
	return render(request, 'invoices/email_invoice.html', {'invoice': invoice})

