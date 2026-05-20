#!/usr/bin/env python
"""Test login functionality"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

print("=" * 60)
print("LOGIN TESTING")
print("=" * 60)

# Check if admin user exists
admin_user = User.objects.filter(username='admin').first()
if admin_user:
    print(f"\n✓ Admin user found: {admin_user.username}")
    print(f"  Email: {admin_user.email}")
else:
    print("\n✗ Admin user not found!")
    exit(1)

# Test authentication
from django.contrib.auth import authenticate
user = authenticate(username='admin', password='Admin123!')
if user:
    print(f"✓ Direct authentication works: {user.username}")
else:
    print("✗ Direct authentication failed!")

# Test login via client
print("\nTesting Django test client login...")
client = Client()

# Get login page
resp = client.get('/login/')
print(f"  GET /login/ -> {resp.status_code}")

# Try to login
resp = client.post('/login/', {
    'username': 'admin',
    'password': 'Admin123!'
})
print(f"  POST /login/ -> {resp.status_code}")

# Check if redirected
location = resp.get('Location', None)
if location:
    print(f"  ✓ Redirected to: {location}")
else:
    print(f"  ✗ No redirect, checking for errors...")
    content = resp.content.decode('utf8')
    if 'Please enter a correct username' in content:
        print("    Found: 'Please enter a correct username' error")
    if 'non_field_errors' in content:
        print("    Found: non_field_errors in response")
    
    # Try to see what form data is being expected
    import re
    # Look for input fields
    username_input = re.search(r'<input[^>]*name=["\']username["\'][^>]*>', content)
    password_input = re.search(r'<input[^>]*name=["\']password["\'][^>]*>', content)
    print(f"    Username input found: {bool(username_input)}")
    print(f"    Password input found: {bool(password_input)}")

print("\n" + "=" * 60)
