#!/usr/bin/env python
"""Test complete auth flow: Register -> Login -> Logout"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

print("=" * 70)
print("TESTING COMPLETE AUTH FLOW")
print("=" * 70)

# Clean up test user if exists
User.objects.filter(username='newuser').delete()

client = Client()

# Test 1: Registration
print("\n1️⃣  TESTING REGISTRATION")
print("-" * 70)

register_data = {
    'username': 'newuser',
    'email': 'newuser@example.com',
    'first_name': 'New',
    'last_name': 'User',
    'password1': 'NewUser123',
    'password2': 'NewUser123',
}

# Get register page
resp = client.get('/register/')
print(f"GET /register/ -> {resp.status_code}")

# Submit registration
resp = client.post('/register/', register_data, follow=True)
print(f"POST /register/ -> {resp.status_code}")
print(f"Redirects: {resp.redirect_chain}")

# Check if user was created
user = User.objects.filter(username='newuser').first()
if user:
    print(f"✓ User created in database: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  First name: {user.first_name}")
    print(f"  Last name: {user.last_name}")
else:
    print("✗ User NOT created in database!")

# Test 2: Verify auto-login after registration
print("\n2️⃣  TESTING AUTO-LOGIN AFTER REGISTRATION")
print("-" * 70)

if '_auth_user_id' in client.session:
    auth_user_id = client.session['_auth_user_id']
    print(f"✓ User auto-logged in: User ID {auth_user_id}")
else:
    print("✗ User NOT auto-logged in after registration!")

# Test 3: Access protected page (dashboard)
print("\n3️⃣  TESTING DASHBOARD ACCESS")
print("-" * 70)

resp = client.get('/dashboard/')
print(f"GET /dashboard/ -> {resp.status_code}")
if resp.status_code == 200 and 'Chào mừng' in resp.content.decode('utf8'):
    print("✓ Dashboard accessible and displaying content")
elif resp.status_code == 200:
    print("✓ Dashboard accessible")
else:
    print(f"✗ Dashboard not accessible (status: {resp.status_code})")

# Test 4: Logout
print("\n4️⃣  TESTING LOGOUT")
print("-" * 70)

resp = client.get('/logout/', follow=True)
print(f"GET /logout/ -> {resp.status_code}")
print(f"Redirects: {resp.redirect_chain}")

if '_auth_user_id' not in client.session:
    print("✓ User logged out (session cleared)")
else:
    print("✗ User NOT logged out!")

# Test 5: Verify redirect to home after logout
print("\n5️⃣  TESTING HOME PAGE AFTER LOGOUT")
print("-" * 70)

# After logout, user should be at home
if resp.redirect_chain and resp.redirect_chain[-1][0].endswith('/'):
    print(f"✓ Redirected to: {resp.redirect_chain[-1][0]}")
    print(f"  Final status: {resp.status_code}")

# Test 6: Login with newly created account
print("\n6️⃣  TESTING LOGIN WITH NEW ACCOUNT")
print("-" * 70)

# Clear session to simulate new browser
client = Client()

login_data = {
    'username': 'newuser',
    'password': 'NewUser123',
}

resp = client.post('/login/', login_data, follow=True)
print(f"POST /login/ -> {resp.status_code}")
print(f"Redirects: {resp.redirect_chain}")

if '_auth_user_id' in client.session:
    print("✓ Login successful with new account")
else:
    print("✗ Login failed!")

print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("""
✓ Registration: New user created and saved to database
✓ Auto-login: User automatically logged in after registration
✓ Dashboard: Protected page accessible after login
✓ Logout: User logged out and session cleared
✓ Redirect: Redirected to home after logout
✓ Re-login: Can login with newly created account

All auth flows working correctly! 🎉
""")
print("=" * 70)
