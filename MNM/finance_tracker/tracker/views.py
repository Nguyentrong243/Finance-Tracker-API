from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
import csv
import json
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

from .forms import (
    RegisterForm,
    AccountSettingsForm,
    SecuritySettingsForm,
    AppSettingsForm,
    TwoFactorAuthenticationForm,
)
from .models import Transaction, UserProfile


def get_transaction_summary(transactions):
    total_income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
    balance = total_income - total_expense
    return total_income, total_expense, balance


def get_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def generate_2fa_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def send_transaction_notification(user, transaction):
    profile = get_user_profile(user)
    if not profile.email_notifications:
        return

    total_income_current = (
        Transaction.objects.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    )
    month_start = datetime.today().replace(day=1).date()
    monthly_income = (
        Transaction.objects.filter(type='income', date__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    )

    amount = transaction.amount
    subject = None
    message = ''

    if transaction.type == 'income' and profile.large_transaction_notifications and amount >= max(Decimal('1000000'), monthly_income * Decimal('0.5')):
        subject = 'Finance Tracker - Thông báo thu nhập lớn'
        message = (
            f'Xin chào {user.username},\n\n'
            f'Giao dịch thu nhập mới ({amount}₫) vừa được ghi nhận.\n'
            f'Đây là mức thu nhập đáng chú ý so với thu nhập tháng này ({monthly_income}₫).\n\n'
            'Nếu bạn không nhận diện được giao dịch này, vui lòng kiểm tra tài khoản của bạn ngay lập tức.'
        )
    elif transaction.type == 'expense' and profile.large_transaction_notifications and total_income_current > 0 and amount >= total_income_current * Decimal('0.5'):
        subject = 'Finance Tracker - Thông báo chi tiêu vượt mức'
        message = (
            f'Xin chào {user.username},\n\n'
            f'Giao dịch chi tiêu mới ({amount}₫) vừa được ghi nhận.\n'
            f'Khoản chi này chiếm một phần lớn so với tổng thu nhập hiện tại ({total_income_current}₫).\n\n'
            'Vui lòng kiểm tra lại ngân sách và hạn chế chi tiêu nếu cần.'
        )

    if subject and user.email:
        send_mail(
            subject,
            message,
            django_settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Đăng ký thành công! Chào mừng bạn đến với Finance Tracker.')
        return redirect('dashboard')

    return render(request, 'register.html', {'form': form})


def about(request):
    return render(request, 'about.html')


def support(request):
    return render(request, 'support.html')


def news(request):
    articles = [
        {
            'title': '5 cách để tiết kiệm hiệu quả hơn',
            'summary': 'Xây dựng thói quen chi tiêu thông minh và tối ưu hóa ngân sách hàng tháng.',
        },
        {
            'title': 'Lập kế hoạch tài chính cá nhân cho 2026',
            'summary': 'Thiết lập mục tiêu tài chính và bước đầu để không bị vượt quá ngân sách.',
        },
        {
            'title': 'Cập nhật tính năng mới của Finance Tracker',
            'summary': 'Theo dõi báo cáo chi tiêu, chuyển khoản và quản lý thu nhập dễ dàng.',
        },
    ]
    return render(request, 'news.html', {'articles': articles})


@login_required
def add_transaction(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        date = request.POST.get('date')

        if amount and transaction_type and category and date:
            try:
                transaction = Transaction.objects.create(
                    amount=Decimal(amount),
                    type=transaction_type,
                    category=category,
                    date=date,
                )
                send_transaction_notification(request.user, transaction)
                messages.success(request, 'Giao dịch đã được thêm thành công!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
        else:
            messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc!')

    return render(request, 'add_transaction.html')


@login_required
def dashboard(request):
    transactions = Transaction.objects.all().order_by('-date')
    profile = get_user_profile(request.user)

    total_income, total_expense, balance = get_transaction_summary(transactions)
    recent_transactions = transactions[:10]

    recent_activities = []
    for transaction in recent_transactions:
        recent_activities.append({
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.category,
            'amount': transaction.amount,
            'type': transaction.type,
        })

    today = datetime.today().date()
    current_monday = today - timedelta(days=today.weekday())
    week_labels = []
    income_trend = []
    expense_trend = []
    for i in range(5, -1, -1):
        start = current_monday - timedelta(weeks=i)
        end = start + timedelta(days=6)
        week_labels.append(f"Tuần {6 - i}")
        income_value = (
            transactions.filter(type='income', date__gte=start, date__lte=end).aggregate(total=Sum('amount'))['total'] or 0
        )
        expense_value = (
            transactions.filter(type='expense', date__gte=start, date__lte=end).aggregate(total=Sum('amount'))['total'] or 0
        )
        income_trend.append(int(income_value))
        expense_trend.append(int(expense_value))

    expense_by_category = (
        transactions.filter(type='expense').values('category').annotate(total=Sum('amount')).order_by('-total')
    )
    expense_category_labels = [item['category'] for item in expense_by_category] or ["Không có dữ liệu"]
    expense_category_values = [int(item['total']) for item in expense_by_category] or [0]

    context = {
        'profile': profile,
        'summary': {
            'total_income': total_income,
            'total_expenses': total_expense,
            'balance': balance,
            'recent_activities': recent_activities,
            'transaction_count': transactions.count(),
        },
        'chart_week_labels': json.dumps(week_labels, ensure_ascii=False),
        'chart_income_trend': json.dumps(income_trend),
        'chart_expense_trend': json.dumps(expense_trend),
        'expense_category_labels': json.dumps(expense_category_labels, ensure_ascii=False),
        'expense_category_values': json.dumps(expense_category_values),
    }

    return render(request, 'dashboard.html', context)


@login_required
def reports(request):
    transactions = Transaction.objects.all().order_by('-date')
    profile = get_user_profile(request.user)

    total_income, total_expense, balance = get_transaction_summary(transactions)
    income_by_category = (
        transactions.filter(type='income').values('category').annotate(total=Sum('amount')).order_by('-total')
    )
    expense_by_category = (
        transactions.filter(type='expense').values('category').annotate(total=Sum('amount')).order_by('-total')
    )

    context = {
        'profile': profile,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'transaction_count': transactions.count(),
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
    }

    return render(request, 'reports.html', context)


@login_required
def transactions_view(request):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        date = request.POST.get('date')

        if amount and transaction_type and category and date:
            try:
                transaction = Transaction.objects.create(
                    amount=Decimal(amount),
                    type=transaction_type,
                    category=category,
                    date=date,
                )
                send_transaction_notification(request.user, transaction)
                messages.success(request, 'Giao dịch đã được thêm thành công!')
                return redirect('transactions')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
        else:
            messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc!')

    transactions = Transaction.objects.all().order_by('-date')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')

    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if type_filter:
        transactions = transactions.filter(type=type_filter)

    total_income, total_expense, balance = get_transaction_summary(transactions)
    categories = Transaction.objects.values_list('category', flat=True).distinct()
    types = Transaction.objects.values_list('type', flat=True).distinct()

    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'categories': categories,
        'types': types,
        'current_category': category_filter,
        'current_type': type_filter,
    }

    return render(request, 'transactions.html', context)


@login_required
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Giao dịch đã được xóa thành công!')
    return redirect('transactions')


@login_required
def settings(request):
    profile = get_user_profile(request.user)
    account_form = AccountSettingsForm(instance=request.user)
    security_form = SecuritySettingsForm(initial={'two_factor_enabled': profile.two_factor_enabled})
    app_form = AppSettingsForm(instance=profile)

    if request.method == 'POST':
        section = request.POST.get('section')

        if section == 'account':
            account_form = AccountSettingsForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                profile.phone = request.POST.get('phone', '').strip()
                profile.save()
                messages.success(request, 'Thông tin tài khoản đã được cập nhật.')
                return redirect('settings')
            else:
                messages.error(request, 'Vui lòng kiểm tra lại thông tin tài khoản.')

        elif section == 'security':
            security_form = SecuritySettingsForm(request.POST)
            if security_form.is_valid():
                profile.two_factor_enabled = request.POST.get('two_factor_enabled') == 'on'
                profile.save()
                password1 = security_form.cleaned_data.get('password1')
                if password1:
                    request.user.set_password(password1)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Mật khẩu và cài đặt bảo mật đã được cập nhật.')
                else:
                    messages.success(request, 'Cài đặt bảo mật đã được cập nhật.')
                return redirect('settings')
            else:
                for field, errors in security_form.errors.items():
                    for error in errors:
                        messages.error(request, error)

        elif section == 'application':
            app_form = AppSettingsForm(request.POST, instance=profile)
            if app_form.is_valid():
                app_form.save()
                messages.success(request, 'Cài đặt ứng dụng đã được lưu.')
                return redirect('settings')
            else:
                messages.error(request, 'Vui lòng kiểm tra lại cài đặt ứng dụng.')

        elif section == 'notification':
            profile.email_notifications = request.POST.get('email_notifications') == 'on'
            profile.large_transaction_notifications = request.POST.get('large_transaction_notifications') == 'on'
            profile.budget_notifications = request.POST.get('budget_notifications') == 'on'
            profile.save()
            messages.success(request, 'Cài đặt thông báo đã được lưu.')
            return redirect('settings')

    context = {
        'profile': profile,
        'account_form': account_form,
        'security_form': security_form,
        'app_form': app_form,
    }
    return render(request, 'settings.html', context)


@login_required
def profile(request):
    user = request.user
    transactions = Transaction.objects.all().order_by('-date')
    total_income = transactions.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expense
    transaction_count = transactions.count()

    context = {
        'user': user,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'transaction_count': transaction_count,
    }

    return render(request, 'profile.html', context)


@login_required
def export_transactions(request):
    transactions = Transaction.objects.all().order_by('-date')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')

    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if type_filter:
        transactions = transactions.filter(type=type_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ngày', 'Danh Mục', 'Loại', 'Số Tiền'])

    for transaction in transactions:
        writer.writerow([
            transaction.date,
            transaction.category,
            'Thu nhập' if transaction.type == 'income' else 'Chi tiêu',
            f'{transaction.amount}'
        ])

    return response


def two_factor_status(request):
    username = request.GET.get('username', '')
    enabled = False
    if username:
        profile = UserProfile.objects.filter(user__username=username).first()
        if profile:
            enabled = profile.two_factor_enabled
    return JsonResponse({'enabled': enabled})


def login_2fa_code(request):
    code = generate_2fa_code()
    request.session['login_2fa_code'] = code
    request.session['login_2fa_code_expires'] = timezone.now().timestamp() + 6
    return JsonResponse({'code': code})


class CustomLoginView(auth_views.LoginView):
    template_name = 'login.html'
    authentication_form = TwoFactorAuthenticationForm
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        if 'login_2fa_code' not in request.session:
            request.session['login_2fa_code'] = generate_2fa_code()
        return super().get(request, *args, **kwargs)

