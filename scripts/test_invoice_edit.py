import os
import sys
from django.utils import timezone

# ensure project root is on path so `config` settings module is importable
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from invoices.models import Invoice, Client as ClientModel, InvoiceItem, BusinessProfile
from invoices.forms import InvoiceForm, InvoiceItemFormSet

User = get_user_model()

username = 'testadmin'
password = 'testpass'

# ensure user exists
user, created = User.objects.get_or_create(username=username, defaults={'email': 'test@example.com'})
if created:
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
else:
    # ensure password known
    user.set_password(password)
    user.save()

# ensure a client exists for this user
client_obj = ClientModel.objects.filter(user=user).first()
if not client_obj:
    client_obj = ClientModel.objects.create(user=user, name='ACME LLC', email='acme@example.com')

# ensure at least one invoice exists for this user
invoice = Invoice.objects.filter(user=user).first()
if not invoice:
    invoice = Invoice.objects.create(user=user, client=client_obj, invoice_number='INV-100', invoice_date=timezone.now().date(), currency='USD')
    InvoiceItem.objects.create(invoice=invoice, description='Item 1', quantity=1, unit_price=10.0, line_total=10.0)

c = Client()
logged = c.login(username=username, password=password)
print('logged in:', logged)

# Prepare POST data using forms to match field names
inv_form = InvoiceForm(instance=invoice)
# copy initial data and normalize None values to empty strings
post_data = inv_form.initial.copy()
for k, v in list(post_data.items()):
    if v is None:
        post_data[k] = ''
# change a simple field
post_data['invoice_number'] = invoice.invoice_number + '-EDIT'
if 'currency' not in post_data:
    post_data['currency'] = 'USD'

# prepare formset POST structure
formset = InvoiceItemFormSet(instance=invoice)
fs_prefix = formset.prefix
post = {}
post[f'{fs_prefix}-TOTAL_FORMS'] = str(formset.total_form_count())
post[f'{fs_prefix}-INITIAL_FORMS'] = str(formset.initial_form_count())
post[f'{fs_prefix}-MIN_NUM_FORMS'] = str(formset.min_num)
post[f'{fs_prefix}-MAX_NUM_FORMS'] = str(formset.max_num)

for i, f in enumerate(formset.forms):
    for name in f.fields:
        key = f'{f.prefix}-{name}'
        # prefer initial, fall back to instance attribute
        val = f.initial.get(name, '')
        if val == '':
            val = getattr(f.instance, name, '')
        # convert non-string simple types to string
        if val is None:
            val = ''
        try:
            # Decimal/date -> str
            val = str(val)
        except Exception:
            pass
        # tweak the first item's description
        if i == 0 and name == 'description':
            val = (val or 'Item 1') + ' edited'
        post[key] = val
    # ensure the management 'id' for existing items is present
    if hasattr(f.instance, 'pk') and f.instance.pk:
        post[f'{f.prefix}-id'] = str(f.instance.pk)

# merge invoice fields
post.update(post_data)

# upload a tiny PNG as business photo
img = SimpleUploadedFile('logo.png', b"\x89PNG\r\n\x1a\n", content_type='image/png')
files = {'business_photo': img}

# include business profile fields to trigger creation/update
post['business_name'] = 'Test Business Ltd'
post['business_email'] = 'biz@test.com'
post['business_phone'] = '123-456-7890'
post['business_address'] = '123 Test St, Testville'

url = reverse('invoice_edit', args=[invoice.pk])
print('POSTing to', url)
# include HTTP_HOST to avoid DisallowedHost from Django testserver default
resp = c.post(url, post, files=files, follow=True, HTTP_HOST='localhost')

print('status code:', resp.status_code)
print('redirect_chain:', resp.redirect_chain)

# collect messages
from django.contrib.messages import get_messages
storage = get_messages(resp.wsgi_request)
print('messages:')
for m in storage:
    print('-', str(m))

# reload invoice and items
invoice.refresh_from_db()
print('invoice_number:', invoice.invoice_number)
items = list(invoice.items.all().values('description', 'quantity', 'unit_price', 'line_total'))
print('items:', items)

# check business profiles for any update
bps = BusinessProfile.objects.filter(user=invoice.user).values('business_name', 'email', 'phone', 'address')
print('business profiles:', list(bps))

print('done')
