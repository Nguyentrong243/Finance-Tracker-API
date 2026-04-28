#!/usr/bin/env python
"""Check what the login form renders"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest

# Create a form
form = AuthenticationForm()

print("=" * 60)
print("LOGIN FORM FIELDS")
print("=" * 60)

for field_name, field in form.fields.items():
    print(f"\nField: {field_name}")
    print(f"  Type: {type(field).__name__}")
    print(f"  Widget: {type(field.widget).__name__}")
    print(f"  Rendered: {field.widget.render(field_name, None, attrs={})[:100]}")

print("\n" + "=" * 60)
print("RENDERED FORM")
print("=" * 60)
print(str(form))
print("=" * 60)
