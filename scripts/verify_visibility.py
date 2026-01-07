import datetime
from django.contrib.auth import get_user_model
from invoices.models import BusinessProfile, Client, Invoice
from django.test import Client as TestClient

User = get_user_model()

def get_or_create_user(username, email):
    u, created = User.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        u.set_password('pass1234')
        u.save()
    return u

u1 = get_or_create_user('user_a','a@example.com')
u2 = get_or_create_user('user_b','b@example.com')

c1, _ = Client.objects.get_or_create(user=u1, name='Client A', defaults={'email':'ca@example.com'})
c2, _ = Client.objects.get_or_create(user=u2, name='Client B', defaults={'email':'cb@example.com'})

inv1, _ = Invoice.objects.get_or_create(invoice_number='A-1', defaults={'user':u1,'client':c1,'invoice_date':datetime.date.today(),'due_date':datetime.date.today()})
inv2, _ = Invoice.objects.get_or_create(invoice_number='B-1', defaults={'user':u2,'client':c2,'invoice_date':datetime.date.today(),'due_date':datetime.date.today()})

# Use Django test client to perform authenticated requests
tc = TestClient()
if not tc.login(username='user_a', password='pass1234'):
    print('Failed to login user_a')
else:
    r = tc.get('/invoices/', HTTP_HOST='localhost')
    txt = r.content.decode('utf-8')
    print('user_a invoice list contains A-1:', 'A-1' in txt)
    print('user_a invoice list contains B-1:', 'B-1' in txt)
    r = tc.get('/invoices/trash/', HTTP_HOST='localhost')
    txt = r.content.decode('utf-8')
    print('user_a invoice trash contains A-1:', 'A-1' in txt)
    print('user_a invoice trash contains B-1:', 'B-1' in txt)
    tc.logout()

if not tc.login(username='user_b', password='pass1234'):
    print('Failed to login user_b')
else:
    r = tc.get('/invoices/', HTTP_HOST='localhost')
    txt = r.content.decode('utf-8')
    print('user_b invoice list contains A-1:', 'A-1' in txt)
    print('user_b invoice list contains B-1:', 'B-1' in txt)
    r = tc.get('/invoices/trash/', HTTP_HOST='localhost')
    txt = r.content.decode('utf-8')
    print('user_b invoice trash contains A-1:', 'A-1' in txt)
    print('user_b invoice trash contains B-1:', 'B-1' in txt)
    tc.logout()

print('Verification script completed.')
