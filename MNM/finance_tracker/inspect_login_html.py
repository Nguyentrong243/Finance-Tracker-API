#!/usr/bin/env python
"""Render login template and inspect the form"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.template.loader import get_template
from django.contrib.auth.forms import AuthenticationForm
from django.test import RequestFactory

factory = RequestFactory()
request = factory.get('/login/')
request.user = __import__('django.contrib.auth.models', fromlist=['AnonymousUser']).AnonymousUser()

# Create form
form = AuthenticationForm()

# Render template
template = get_template('login.html')
context = {'form': form}

html = template.render(context, request)

# Check if form fields are in the HTML
print("=" * 60)
print("CHECKING LOGIN FORM HTML")
print("=" * 60)

checks = {
    'has_form_tag': '<form' in html and 'method="post"' in html,
    'has_csrf_token': '{% csrf_token %}' in html or 'csrfmiddlewaretoken' in html,
    'has_username_field': 'name="username"' in html or 'id_username' in html,
    'has_password_field': 'name="password"' in html or 'id_password' in html,
    'has_submit_button': 'type="submit"' in html,
}

for check, result in checks.items():
    symbol = "✓" if result else "✗"
    print(f"{symbol} {check}")

print("\n" + "=" * 60)
print("FORM SNIPPET")
print("=" * 60)

# Extract form section
import re
form_match = re.search(r'<form.*?</form>', html, re.DOTALL)
if form_match:
    form_html = form_match.group()
    # Print first 1000 chars
    print(form_html[:1000])
    if len(form_html) > 1000:
        print("...")
else:
    print("Could not extract form")

print("\n" + "=" * 60)
