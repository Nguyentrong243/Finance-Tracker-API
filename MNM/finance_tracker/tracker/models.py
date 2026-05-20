from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
import calendar
from datetime import datetime, timedelta


class UserProfile(models.Model):
    THEME_CHOICES = (
        ('light', 'Sáng'),
        ('dark', 'Tối'),
    )

    CURRENCY_CHOICES = (
        ('vnd', 'Đồng Việt Nam (₫)'),
        ('usd', 'Dollar Mỹ ($)'),
        ('eur', 'Euro (€)'),
    )

    DATE_FORMAT_CHOICES = (
        ('dd/mm/yyyy', 'DD/MM/YYYY'),
        ('mm/dd/yyyy', 'MM/DD/YYYY'),
        ('yyyy-mm-dd', 'YYYY-MM-DD'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    theme_mode = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    two_factor_enabled = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)
    large_transaction_notifications = models.BooleanField(default=True)
    budget_notifications = models.BooleanField(default=True)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='vnd')
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default='dd/mm/yyyy')

    def __str__(self):
        return f"{self.user.username} profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


def get_or_create_user_profile(self):
    profile, _ = UserProfile.objects.get_or_create(user=self)
    return profile

User.add_to_class('settings_profile', property(get_or_create_user_profile))


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]

    STATUS_CHOICES = [
        ('posted', 'Đã xác nhận'),
        ('pending', 'Chờ xác nhận'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=100)
    date = models.DateField()
    wallet = models.CharField(max_length=100, default='Ví chính', blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='posted')
    recurring = models.ForeignKey('RecurringTransaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='transactions')
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.category} - {self.amount}đ"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=100)
    monthly_limit = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])
    month = models.DateField()  # First day of the month
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'category', 'month')

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.monthly_limit}đ"


class SavingsGoal(models.Model):
    STATUS_CHOICES = [
        ('active', 'Đang hoạt động'),
        ('completed', 'Hoàn tất'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])
    saved_amount = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(Decimal('0'))], default=Decimal('0'))
    target_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name} - {self.target_amount}đ"

    @property
    def remaining_amount(self):
        remaining = self.target_amount - self.saved_amount
        return remaining if remaining > 0 else 0

    @property
    def progress_percentage(self):
        if self.target_amount and self.target_amount > 0:
            progress = (self.saved_amount / self.target_amount) * 100
            return round(progress, 1)
        return 0


class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần'),
        ('biweekly', 'Hai tuần một lần'),
        ('monthly', 'Hàng tháng'),
        ('quarterly', 'Hàng quý'),
        ('yearly', 'Hàng năm'),
        ('custom', 'Tùy chỉnh'),
    ]

    STATUS_CHOICES = [
        ('active', 'Hoạt động'),
        ('paused', 'Tạm dừng'),
        ('completed', 'Hoàn tất'),
    ]

    EXECUTION_MODE_CHOICES = [
        ('auto', 'Tự động thực hiện'),
        ('pending', 'Chờ xác nhận'),
    ]

    INTERVAL_UNIT_CHOICES = [
        ('days', 'Ngày'),
        ('weeks', 'Tuần'),
    ]

    WEEKDAY_CHOICES = [
        (0, 'Thứ Hai'),
        (1, 'Thứ Ba'),
        (2, 'Thứ Tư'),
        (3, 'Thứ Năm'),
        (4, 'Thứ Sáu'),
        (5, 'Thứ Bảy'),
        (6, 'Chủ Nhật'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=0, validators=[MinValueValidator(Decimal('0'))])
    type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPES)
    category = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    wallet = models.CharField(max_length=100, default='Ví chính', blank=True)
    notes = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    max_occurrences = models.PositiveIntegerField(null=True, blank=True)
    occurrences = models.PositiveIntegerField(default=0)
    execution_mode = models.CharField(max_length=10, choices=EXECUTION_MODE_CHOICES, default='auto')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    next_run_date = models.DateField(null=True, blank=True)
    last_generated = models.DateField(null=True, blank=True)
    monthly_day = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)])
    is_last_day_of_month = models.BooleanField(default=False)
    monthly_week = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    monthly_weekday = models.PositiveSmallIntegerField(null=True, blank=True, choices=WEEKDAY_CHOICES)
    custom_interval = models.PositiveIntegerField(null=True, blank=True)
    custom_interval_unit = models.CharField(max_length=10, choices=INTERVAL_UNIT_CHOICES, null=True, blank=True)
    cron_expression = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['next_run_date']),
            models.Index(fields=['status']),
            models.Index(fields=['execution_mode']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.frequency} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status in ['paused', 'completed']:
            self.is_active = False
        elif self.status == 'active':
            self.is_active = True

        if not self.next_run_date and self.start_date:
            self.next_run_date = self.start_date

        super().save(*args, **kwargs)

    @staticmethod
    def _last_day_of_month(year, month):
        return calendar.monthrange(year, month)[1]

    @staticmethod
    def _nth_weekday(year, month, week, weekday):
        first_day, days_in_month = calendar.monthrange(year, month)
        first_weekday = (weekday - first_day + 7) % 7
        day = first_weekday + 1 + (week - 1) * 7
        if day > days_in_month:
            return None
        return datetime(year, month, day).date()

    def compute_next_run_date(self, from_date=None):
        if not self.start_date:
            return None

        if from_date is None:
            from_date = self.next_run_date or self.start_date

        if self.frequency == 'daily':
            return from_date + timedelta(days=1)

        if self.frequency == 'weekly':
            return from_date + timedelta(weeks=1)

        if self.frequency == 'biweekly':
            return from_date + timedelta(weeks=2)

        if self.frequency == 'monthly':
            month = from_date.month + 1
            year = from_date.year
            if month > 12:
                month = 1
                year += 1

            if self.is_last_day_of_month:
                day = self._last_day_of_month(year, month)
            elif self.monthly_day:
                day = min(self.monthly_day, self._last_day_of_month(year, month))
            elif self.monthly_week and self.monthly_weekday is not None:
                next_date = self._nth_weekday(year, month, self.monthly_week, self.monthly_weekday)
                if next_date:
                    return next_date
                day = min(from_date.day, self._last_day_of_month(year, month))
            else:
                day = min(from_date.day, self._last_day_of_month(year, month))

            return from_date.replace(year=year, month=month, day=day)

        if self.frequency == 'quarterly':
            month = from_date.month + 3
            year = from_date.year
            while month > 12:
                month -= 12
                year += 1

            if self.is_last_day_of_month:
                day = self._last_day_of_month(year, month)
            elif self.monthly_day:
                day = min(self.monthly_day, self._last_day_of_month(year, month))
            elif self.monthly_week and self.monthly_weekday is not None:
                next_date = self._nth_weekday(year, month, self.monthly_week, self.monthly_weekday)
                if next_date:
                    return next_date
                day = min(from_date.day, self._last_day_of_month(year, month))
            else:
                day = min(from_date.day, self._last_day_of_month(year, month))

            return from_date.replace(year=year, month=month, day=day)

        if self.frequency == 'yearly':
            try:
                return from_date.replace(year=from_date.year + 1)
            except ValueError:
                return from_date.replace(year=from_date.year + 1, month=2, day=28)

        if self.frequency == 'custom':
            if self.custom_interval and self.custom_interval_unit == 'days':
                return from_date + timedelta(days=self.custom_interval)
            if self.custom_interval and self.custom_interval_unit == 'weeks':
                return from_date + timedelta(weeks=self.custom_interval)

        return from_date + timedelta(days=1)

    def is_due(self, today=None):
        today = today or timezone.now().date()
        return self.next_run_date is not None and self.next_run_date <= today and self.status == 'active'
