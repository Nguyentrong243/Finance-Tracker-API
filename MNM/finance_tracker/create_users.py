#!/usr/bin/env python
"""Create test users for Finance Tracker"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth.models import User

def create_users():
    # Create admin user
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Admin',
            'last_name': 'User'
        }
    )
    if created:
        admin.set_password('Admin123!')
        admin.save()
        print('✓ Admin user created')
        print(f'  Username: admin')
        print(f'  Password: Admin123!')
    else:
        # Reset password anyway
        admin.set_password('Admin123!')
        admin.save()
        print('✓ Admin user already exists (password reset to Admin123!)')
    
    # Create test user
    testuser, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'testuser@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        testuser.set_password('Test123!')
        testuser.save()
        print('\n✓ Test user created')
        print(f'  Username: testuser')
        print(f'  Password: Test123!')
    else:
        # Reset password anyway
        testuser.set_password('Test123!')
        testuser.save()
        print('\n✓ Test user already exists (password reset to Test123!)')
    
    # List all users
    print('\n' + '='*50)
    print('📋 ALL USERS IN DATABASE:')
    print('='*50)
    users = User.objects.all()
    if users.exists():
        for user in users:
            role = 'Admin' if user.is_superuser else 'User'
            print(f'  • {user.username:15} | {user.email:25} | {role}')
    else:
        print('  No users found')
    print('='*50)

if __name__ == '__main__':
    create_users()
