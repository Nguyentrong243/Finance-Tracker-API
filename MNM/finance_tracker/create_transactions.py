#!/usr/bin/env python
"""Create test transactions for Finance Tracker"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from tracker.models import Transaction

def create_test_transactions():
    # Clear existing transactions
    Transaction.objects.all().delete()
    
    today = datetime.now().date()
    
    # Create sample income transactions
    income_data = [
        {'date': today - timedelta(days=30), 'amount': 10000000, 'category': 'Salary'},
        {'date': today - timedelta(days=15), 'amount': 2000000, 'category': 'Freelance'},
        {'date': today - timedelta(days=7), 'amount': 1500000, 'category': 'Bonus'},
        {'date': today - timedelta(days=2), 'amount': 500000, 'category': 'Gift'},
    ]
    
    # Create sample expense transactions
    expense_data = [
        {'date': today - timedelta(days=28), 'amount': 2500000, 'category': 'Ăn uống'},
        {'date': today - timedelta(days=25), 'amount': 1800000, 'category': 'Mua sắm'},
        {'date': today - timedelta(days=20), 'amount': 3000000, 'category': 'Giao thông'},
        {'date': today - timedelta(days=15), 'amount': 2000000, 'category': 'Giải trí'},
        {'date': today - timedelta(days=10), 'amount': 1200000, 'category': 'Ăn uống'},
        {'date': today - timedelta(days=5), 'amount': 1500000, 'category': 'Mua sắm'},
        {'date': today - timedelta(days=1), 'amount': 800000, 'category': 'Ăn uống'},
    ]
    
    # Create income transactions
    print('Creating income transactions...')
    for data in income_data:
        transaction = Transaction.objects.create(
            amount=Decimal(str(data['amount'])),
            type='income',
            category=data['category'],
            date=data['date']
        )
        print(f'  ✓ Income: {data["category"]} | {data["amount"]:,}₫ | {data["date"]}')
    
    # Create expense transactions
    print('\nCreating expense transactions...')
    for data in expense_data:
        transaction = Transaction.objects.create(
            amount=Decimal(str(data['amount'])),
            type='expense',
            category=data['category'],
            date=data['date']
        )
        print(f'  ✓ Expense: {data["category"]} | {data["amount"]:,}₫ | {data["date"]}')
    
    # Calculate totals
    total_income = sum(Decimal(str(d['amount'])) for d in income_data)
    total_expense = sum(Decimal(str(d['amount'])) for d in expense_data)
    balance = total_income - total_expense
    
    print('\n' + '='*60)
    print('📊 TRANSACTION SUMMARY:')
    print('='*60)
    print(f'  Total Income:  {float(total_income):>15,.0f}₫')
    print(f'  Total Expense: {float(total_expense):>15,.0f}₫')
    print(f'  Balance:       {float(balance):>15,.0f}₫')
    print('='*60)
    print(f'  Total Transactions: {Transaction.objects.count()}')
    print('='*60)

if __name__ == '__main__':
    create_test_transactions()
