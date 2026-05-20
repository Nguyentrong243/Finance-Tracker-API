from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Sum, Q
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.core.management import call_command
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
from .models import Transaction, UserProfile, Budget, RecurringTransaction, SavingsGoal


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


def get_budget_progress(user, month_start):
    """Get budget progress for all categories in a given month"""
    budgets = Budget.objects.filter(user=user, month=month_start)
    progress_data = []
    
    for budget in budgets:
        month_end = month_start + timedelta(days=32)
        month_end = month_end.replace(day=1) - timedelta(days=1)
        spent = (
            Transaction.objects.filter(
                user=user,
                category=budget.category,
                type='expense',
                date__gte=month_start,
                date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        percentage = int((spent / budget.monthly_limit * 100)) if budget.monthly_limit > 0 else 0
        progress_data.append({
            'category': budget.category,
            'limit': budget.monthly_limit,
            'spent': spent,
            'remaining': max(0, budget.monthly_limit - spent),
            'percentage': min(percentage, 100),
            'warning': percentage >= 80,
        })
    
    return progress_data


def send_transaction_notification(user, transaction):
    profile = get_user_profile(user)
    if not profile.email_notifications:
        return

    total_income_current = (
        Transaction.objects.filter(user=user, type='income').aggregate(total=Sum('amount'))['total'] or 0
    )
    month_start = datetime.today().replace(day=1).date()
    monthly_income = (
        Transaction.objects.filter(user=user, type='income', date__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
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
        try:
            send_mail(
                subject,
                message,
                django_settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            pass


def check_budget_alerts(user, transaction):
    """Check if transaction triggers budget alert"""
    if transaction.type != 'expense':
        return
    
    month_start = transaction.date.replace(day=1)
    budget = Budget.objects.filter(user=user, category=transaction.category, month=month_start).first()
    
    if not budget:
        return
    
    month_end = month_start + timedelta(days=32)
    month_end = month_end.replace(day=1) - timedelta(days=1)
    spent = (
        Transaction.objects.filter(
            user=user,
            category=budget.category,
            type='expense',
            date__gte=month_start,
            date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
    )
    percentage = (spent / budget.monthly_limit * 100) if budget.monthly_limit > 0 else 0
    
    profile = get_user_profile(user)
    if percentage >= 80 and profile.budget_notifications and user.email:
        subject = 'Finance Tracker - Cảnh báo ngân sách'
        message_text = ''
        if percentage >= 100:
            message_text = (
                f'Xin chào {user.username},\n\n'
                f'Bạn đã vượt quá ngân sách cho danh mục {transaction.category}!\n'
                f'Ngân sách: {budget.monthly_limit}đ | Đã tiêu: {spent}đ\n\n'
                'Vui lòng kiểm tra lại chi tiêu của bạn.'
            )
        else:
            message_text = (
                f'Xin chào {user.username},\n\n'
                f'Chi tiêu danh mục {transaction.category} đã đạt {percentage:.0f}% ngân sách!\n'
                f'Ngân sách: {budget.monthly_limit}đ | Đã tiêu: {spent}đ\n\n'
                'Hãy cẩn thận với các chi tiêu tiếp theo.'
            )
        try:
            send_mail(
                subject,
                message_text,
                django_settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            pass


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
        wallet = request.POST.get('wallet', 'Ví chính')
        notes = request.POST.get('notes', '')

        if amount and transaction_type and category and date:
            try:
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=Decimal(amount),
                    type=transaction_type,
                    category=category,
                    date=date,
                    wallet=wallet,
                    notes=notes,
                )
                send_transaction_notification(request.user, transaction)
                check_budget_alerts(request.user, transaction)
                messages.success(request, 'Giao dịch đã được thêm thành công!')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
        else:
            messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc!')

    wallets = Transaction.objects.filter(user=request.user).values_list('wallet', flat=True).distinct()
    return render(request, 'add_transaction.html', {'wallets': wallets})


@login_required
def dashboard(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
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

    month_start = datetime.today().replace(day=1).date()
    budget_progress = get_budget_progress(request.user, month_start)

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
        'budget_progress': budget_progress,
        'chart_week_labels': json.dumps(week_labels, ensure_ascii=False),
        'chart_income_trend': json.dumps(income_trend),
        'chart_expense_trend': json.dumps(expense_trend),
        'expense_category_labels': json.dumps(expense_category_labels, ensure_ascii=False),
        'expense_category_values': json.dumps(expense_category_values),
    }

    return render(request, 'dashboard.html', context)


@login_required
def reports(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
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
        view_type = request.POST.get('view', 'transactions')
        
        # Handle recurring transactions actions
        if view_type == 'recurring':
            action = request.POST.get('action')
            
            if action == 'generate':
                try:
                    call_command('generate_recurring_transactions', user_id=request.user.id)
                    messages.success(request, 'Giao dịch định kỳ đã được thực hiện thành công!')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')
            
            elif action == 'add_recurring':
                try:
                    amount_raw = request.POST.get('recurring_amount', '').replace(',', '').strip()
                    r_type = request.POST.get('recurring_type', '').strip()
                    r_category = request.POST.get('recurring_category', '').strip()
                    r_frequency = request.POST.get('recurring_frequency', '').strip()
                    r_start_date = request.POST.get('recurring_start_date', '').strip()
                    r_end_date = request.POST.get('recurring_end_date', '').strip() or None
                    r_interval = request.POST.get('recurring_interval', '').strip()
                    r_notes = request.POST.get('recurring_notes', '').strip()

                    if not all([amount_raw, r_type, r_category, r_frequency, r_start_date]):
                        messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc!')
                    else:
                        kwargs = dict(
                            user=request.user,
                            amount=Decimal(amount_raw),
                            type=r_type,
                            category=r_category,
                            frequency=r_frequency,
                            start_date=r_start_date,
                            end_date=r_end_date,
                            notes=r_notes,
                            status='active',
                            is_active=True,
                        )
                        if r_frequency == 'custom' and r_interval:
                            kwargs['custom_interval'] = int(r_interval)
                            kwargs['custom_interval_unit'] = 'days'
                        new_recurring = RecurringTransaction.objects.create(**kwargs)
                        # Nếu start_date <= hôm nay thì generate ngay
                        today_date = timezone.now().date()
                        start_d = new_recurring.start_date
                        if start_d <= today_date:
                            call_command('generate_recurring_transactions', user_id=request.user.id)
                            messages.success(request, f'Đã thêm và tự động thực hiện giao dịch định kỳ "{r_category}"!')
                        else:
                            messages.success(request, f'Đã thêm giao dịch định kỳ "{r_category}". Sẽ thực hiện từ {new_recurring.start_date.strftime("%d/%m/%Y")}.')
                except Exception as e:
                    messages.error(request, f'Lỗi khi thêm giao dịch định kỳ: {str(e)}')

            elif action == 'toggle':
                recurring_id = request.POST.get('recurring_id')
                try:
                    recurring = RecurringTransaction.objects.get(id=recurring_id, user=request.user)
                    recurring.is_active = not recurring.is_active
                    recurring.status = 'active' if recurring.is_active else 'paused'
                    recurring.save()
                    status = 'kích hoạt' if recurring.is_active else 'tạm dừng'
                    messages.success(request, f'Giao dịch định kỳ đã được {status}.')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')
            
            elif action == 'delete':
                recurring_id = request.POST.get('recurring_id')
                try:
                    RecurringTransaction.objects.filter(id=recurring_id, user=request.user).delete()
                    messages.success(request, 'Giao dịch định kỳ đã được xóa.')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')
            
            return redirect('transactions')
        
        elif view_type == 'savings':
            action = request.POST.get('action')
            if action == 'add_savings':
                try:
                    amount_raw = request.POST.get('savings_target_amount', '').replace(',', '').strip()
                    saved_raw = request.POST.get('savings_saved_amount', '0').replace(',', '').strip() or '0'
                    name = request.POST.get('savings_name', '').strip()
                    target_date = request.POST.get('savings_target_date', '').strip()
                    notes = request.POST.get('savings_notes', '').strip()

                    if not all([amount_raw, name, target_date]):
                        messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc của tiết kiệm!')
                    else:
                        SavingsGoal.objects.create(
                            user=request.user,
                            name=name,
                            target_amount=Decimal(amount_raw),
                            saved_amount=Decimal(saved_raw),
                            target_date=target_date,
                            notes=notes,
                            status='active',
                        )
                        messages.success(request, f'Đã thêm mục tiêu tiết kiệm "{name}".')
                except Exception as e:
                    messages.error(request, f'Lỗi khi thêm mục tiêu tiết kiệm: {str(e)}')

            elif action == 'toggle':
                savings_id = request.POST.get('savings_id')
                try:
                    savings_goal = SavingsGoal.objects.get(id=savings_id, user=request.user)
                    savings_goal.status = 'completed' if savings_goal.status == 'active' else 'active'
                    savings_goal.save()
                    status_text = 'hoàn tất' if savings_goal.status == 'completed' else 'đang hoạt động'
                    messages.success(request, f'Mục tiêu tiết kiệm đã chuyển thành trạng thái {status_text}.')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')

            elif action == 'delete':
                savings_id = request.POST.get('savings_id')
                try:
                    SavingsGoal.objects.filter(id=savings_id, user=request.user).delete()
                    messages.success(request, 'Mục tiêu tiết kiệm đã được xóa.')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')

            return redirect('transactions')
        
        # Handle regular transaction creation
        amount = request.POST.get('amount')
        transaction_type = request.POST.get('transaction_type')
        category = request.POST.get('category')
        date = request.POST.get('date')
        wallet = request.POST.get('wallet', 'Ví chính')
        notes = request.POST.get('notes', '')

        if amount and transaction_type and category and date:
            try:
                transaction = Transaction.objects.create(
                    user=request.user,
                    amount=Decimal(amount),
                    type=transaction_type,
                    category=category,
                    date=date,
                    wallet=wallet,
                    notes=notes,
                )
                send_transaction_notification(request.user, transaction)
                check_budget_alerts(request.user, transaction)
                messages.success(request, 'Giao dịch đã được thêm thành công!')
                return redirect('transactions')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
        else:
            messages.error(request, 'Vui lòng điền đầy đủ các trường bắt buộc!')

    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')
    wallet_filter = request.GET.get('wallet', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')

    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if type_filter:
        transactions = transactions.filter(type=type_filter)
    if wallet_filter:
        transactions = transactions.filter(wallet=wallet_filter)
    if start_date:
        try:
            transactions = transactions.filter(date__gte=start_date)
        except:
            pass
    if end_date:
        try:
            transactions = transactions.filter(date__lte=end_date)
        except:
            pass
    if search_query:
        transactions = transactions.filter(
            Q(category__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(wallet__icontains=search_query)
        )

    total_income, total_expense, balance = get_transaction_summary(transactions)
    categories = Transaction.objects.filter(user=request.user).values_list('category', flat=True).distinct()
    types = Transaction.objects.filter(user=request.user).values_list('type', flat=True).distinct()
    wallets = Transaction.objects.filter(user=request.user).values_list('wallet', flat=True).distinct()
    profile = get_user_profile(request.user)
    
    # Get recurring transactions - annotate next_date directly on each object
    recurring_qs = RecurringTransaction.objects.filter(user=request.user).order_by('-created_at')
    for r in recurring_qs:
        r.next_date = get_next_recurring_date(r)
    recurring_transactions = recurring_qs

    savings_goals = SavingsGoal.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'categories': categories,
        'types': types,
        'wallets': wallets,
        'current_category': category_filter,
        'current_type': type_filter,
        'current_wallet': wallet_filter,
        'current_start_date': start_date,
        'current_end_date': end_date,
        'search_query': search_query,
        'profile': profile,
        'recurring_transactions': recurring_transactions,
        'savings_goals': savings_goals,
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
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
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
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')

    if category_filter:
        transactions = transactions.filter(category=category_filter)
    if type_filter:
        transactions = transactions.filter(type=type_filter)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    response.write('\ufeff')

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

    def form_valid(self, form):
        """Xử lý login thành công"""
        user = form.get_user()
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self):
        """Chuyển hướng sau khi login"""
        return self.request.GET.get('next', reverse('dashboard')) if 'next' in self.request.GET else reverse('dashboard')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        if 'login_2fa_code' not in request.session:
            request.session['login_2fa_code'] = generate_2fa_code()
        return super().get(request, *args, **kwargs)


@login_required
def budgets(request):
    """Manage budgets"""
    month = request.GET.get('month', datetime.today().replace(day=1).date().isoformat())
    try:
        if len(month) == 7:
            month_date = datetime.fromisoformat(f'{month}-01').date()
        else:
            month_date = datetime.fromisoformat(month).date()
    except:
        month_date = datetime.today().replace(day=1).date()
    
    budgets = Budget.objects.filter(user=request.user, month=month_date)
    budget_progress = get_budget_progress(request.user, month_date)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            category = request.POST.get('category', '').strip()
            limit = request.POST.get('limit', '').strip()
            if category and limit:
                try:
                    Budget.objects.update_or_create(
                        user=request.user,
                        category=category,
                        month=month_date,
                        defaults={'monthly_limit': Decimal(limit)}
                    )
                    messages.success(request, f'Ngân sách cho {category} đã được cập nhật.')
                except Exception as e:
                    messages.error(request, f'Lỗi: {str(e)}')
                return redirect(f'/budgets/?month={month}')
        
        elif action == 'delete':
            budget_id = request.POST.get('budget_id')
            try:
                Budget.objects.filter(id=budget_id, user=request.user).delete()
                messages.success(request, 'Ngân sách đã được xóa.')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
            return redirect(f'/budgets/?month={month}')
    
    # Calculate summary totals
    total_budget = sum(item['limit'] for item in budget_progress)
    total_spent = sum(item['spent'] for item in budget_progress)
    total_remaining = sum(item['remaining'] for item in budget_progress)
    
    context = {
        'budgets': budgets,
        'budget_progress': budget_progress,
        'month': month_date,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'total_remaining': total_remaining,
    }
    return render(request, 'budgets.html', context)


def get_next_recurring_date(recurring):
    """
    Ngày tiếp theo sẽ thực hiện:
    - Chưa chạy lần nào: trả về start_date
    - Đã chạy ít nhất 1 lần: trả về next_run_date (đã update sau mỗi lần generate)
    """
    if recurring.next_run_date:
        return recurring.next_run_date
    return recurring.start_date

@login_required
def recurring_transactions(request):
    """Manage recurring transactions"""
    recurring = RecurringTransaction.objects.filter(user=request.user)
    recurring_transactions = []
    for tx in recurring:
        recurring_transactions.append({
            'tx': tx,
            'next_date': get_next_recurring_date(tx),
        })
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            try:
                RecurringTransaction.objects.create(
                    user=request.user,
                    amount=Decimal(request.POST.get('amount', 0)),
                    type=request.POST.get('type'),
                    category=request.POST.get('category'),
                    frequency=request.POST.get('frequency'),
                    wallet=request.POST.get('wallet', 'Ví chính'),
                    notes=request.POST.get('notes', ''),
                    start_date=request.POST.get('start_date'),
                    end_date=request.POST.get('end_date') or None,
                )
                messages.success(request, 'Giao dịch định kỳ đã được tạo.')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
            return redirect('recurring_transactions')
        
        elif action == 'generate':
            try:
                call_command('generate_recurring_transactions')
                messages.success(request, 'Giao dịch định kỳ đã được tạo tự động.')
            except Exception as e:
                messages.error(request, f'Lỗi khi tạo giao dịch định kỳ: {str(e)}')
            return redirect('recurring_transactions')
        
        elif action == 'toggle':
            recurring_id = request.POST.get('recurring_id')
            try:
                recurring_tx = RecurringTransaction.objects.filter(id=recurring_id, user=request.user).first()
                if recurring_tx:
                    recurring_tx.is_active = not recurring_tx.is_active
                    recurring_tx.status = 'active' if recurring_tx.is_active else 'paused'
                    recurring_tx.save()
                    messages.success(request, 'Giao dịch định kỳ đã được cập nhật.')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
            return redirect('recurring_transactions')
        
        elif action == 'delete':
            recurring_id = request.POST.get('recurring_id')
            try:
                RecurringTransaction.objects.filter(id=recurring_id, user=request.user).delete()
                messages.success(request, 'Giao dịch định kỳ đã được xóa.')
            except Exception as e:
                messages.error(request, f'Lỗi: {str(e)}')
            return redirect('recurring_transactions')
    
    context = {
        'recurring_transactions': recurring_transactions,
    }
    return render(request, 'recurring_transactions.html', context)

