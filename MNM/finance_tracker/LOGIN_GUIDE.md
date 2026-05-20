# 📋 Finance Tracker - Login Test Guide

## ✅ Configuration Status

- ✓ Django database configured (SQLite)
- ✓ User accounts created
- ✓ Passwords reset
- ✓ Form rendering correctly
- ✓ ALLOWED_HOSTS configured

## 🔐 Updated Credentials

### Admin Account

```
URL: http://127.0.0.1:8000/admin/
Username: admin
Password: Admin123
```

### Test User Account

```
URL: http://127.0.0.1:8000/login/
Username: testuser
Password: Test123
```

## 🚀 Step-by-Step Test

### 1. Test Login Page

- Open: http://127.0.0.1:8000/login/
- You should see the login form with:
  - Username field (Tên đăng nhập)
  - Password field (Mật khẩu) with eye icon toggle
  - Login button (Đăng nhập)
  - Register link (Đăng ký ngay)

### 2. Test Login with Test User

1. Click on password field to focus
2. Type: `Test123` (without quotes, no special characters)
3. Click "Đăng nhập" button
4. **Expected**: Should redirect to `/dashboard/`

### 3. Test Dashboard

- Should see:
  - "Chào mừng, testuser!" greeting
  - 3 stat cards (Income, Expense, Balance)
  - 2 charts (Income vs Expense, Expense by Category)
  - Recent transactions list

### 4. Test Admin Panel

1. Open: http://127.0.0.1:8000/admin/
2. Username: `admin`
3. Password: `Admin123`
4. Should see Django admin dashboard

## 🔍 Troubleshooting

If login still fails:

1. **Check password**: Make sure you type exactly: `Admin123` or `Test123`
2. **Check Caps Lock**: Password is case-sensitive
3. **Browser Cache**: Clear browser cache/cookies and try again
4. **JavaScript**: Make sure password toggle button works (click eye icon)
5. **Server**: Make sure Django development server is still running

## 📊 Sample Data

- Total Income: 14,000,000₫
- Total Expense: 12,800,000₫
- Balance: 1,200,000₫
- 11 sample transactions in database

## 📝 Notes

- Passwords were changed to simpler versions (no special characters)
- ALLOWED_HOSTS now accepts all hosts for development
- All forms validate with CSRF protection
- Authentication middleware is configured correctly
