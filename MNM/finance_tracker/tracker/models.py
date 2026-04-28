from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta


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
    TYPE_CHOICES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.type} - {self.amount}"


class RecurringTransaction(models.Model):
    FREQUENCY_CHOICES = (
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần'),
        ('monthly', 'Hàng tháng'),
    )

    TYPE_CHOICES = (
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=100)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    next_due_date = models.DateField()
    reminder_days_before = models.IntegerField(default=0, help_text="Số ngày nhắc trước hạn")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.amount}₫ ({self.frequency})"

    def get_next_due_date(self, current_date):
        if self.frequency == 'daily':
            return current_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return current_date + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            try:
                return current_date.replace(month=current_date.month + 1)
            except ValueError:
                return current_date.replace(year=current_date.year + 1, month=1)