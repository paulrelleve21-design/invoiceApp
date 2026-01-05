import os
import sys
import secrets

# Configure Django settings
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or secrets.token_urlsafe(12)

if User.objects.filter(username=username).exists():
    print(f"Superuser '{username}' already exists. No changes made.")
else:
    User.objects.create_superuser(username=username, email=email, password=password)
    print('Superuser created:')
    print(f'  username: {username}')
    print(f'  email: {email}')
    print(f'  password: {password}')
