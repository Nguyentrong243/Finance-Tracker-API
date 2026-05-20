from pathlib import Path
import re

path = Path('tracker/models.py')
text = path.read_text(encoding='utf-8')
pattern = re.compile(r'class RecurringTransaction\(models\.Model\):[\s\S]*$', re.MULTILINE)
new = '''class RecurringTransaction(models.Model):
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
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    wallet = models.CharField(max_length=100, default='Ví chính', blank=True)
    notes = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    max_occurrences = models.PositiveIntegerField(null=True, blank=True)
    occurrences = models.PositiveIntegerField(default=0)
    execution_mode = models.CharField(max_length=10, choices=EXECUTION_MODE_CHOICES, default='auto')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
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
        ]

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.get_frequency_display()}"

    def save(self, *args, **kwargs):
        if not self.next_run_date and self.start_date:
            self.next_run_date = self.start_date
        super().save(*args, **kwargs)

    @staticmethod
    def _last_day_of_month(year, month):
        return calendar.monthrange(year, month)[1]

    @staticmethod
    def _nth_weekday(year, month, weekday, week_number):
        month_calendar = calendar.Calendar().monthdatescalendar(year, month)
        occurrences = [day for week in month_calendar for day in week if day.weekday() == weekday and day.month == month]
        if not occurrences:
            return None
        if week_number == 5:
            return occurrences[-1]
        return occurrences[week_number - 1] if 0 <= week_number - 1 < len(occurrences) else None

    def compute_next_run_date(self, from_date=None):
        if not from_date:
            from_date = self.next_run_date or self.start_date
        if self.frequency == 'daily':
            return from_date + timedelta(days=1)
        if self.frequency == 'weekly':
            return from_date + timedelta(weeks=1)
        if self.frequency == 'biweekly':
            return from_date + timedelta(weeks=2)
        if self.frequency == 'custom' and self.custom_interval and self.custom_interval_unit:
            if self.custom_interval_unit == 'days':
                return from_date + timedelta(days=self.custom_interval)
            return from_date + timedelta(weeks=self.custom_interval)

        if self.frequency in ['monthly', 'quarterly', 'yearly']:
            year = from_date.year
            month = from_date.month
            day = from_date.day

            if self.frequency == 'monthly':
                month += 1
            elif self.frequency == 'quarterly':
                month += 3
            elif self.frequency == 'yearly':
                year += 1

            while month > 12:
                month -= 12
                year += 1

            if self.monthly_day:
                day = min(self.monthly_day, self._last_day_of_month(year, month))
            elif self.is_last_day_of_month:
                day = self._last_day_of_month(year, month)
            elif self.monthly_week and self.monthly_weekday is not None:
                next_date = self._nth_weekday(year, month, self.monthly_weekday, self.monthly_week)
                return next_date
            else:
                day = min(day, self._last_day_of_month(year, month))

            return from_date.replace(year=year, month=month, day=day)

        return from_date

    def get_schedule_label(self):
        if self.frequency == 'daily':
            return 'Hàng ngày'
        if self.frequency == 'weekly':
            return 'Hàng tuần'
        if self.frequency == 'biweekly':
            return 'Hai tuần một lần'
        if self.frequency == 'monthly':
            if self.is_last_day_of_month:
                return 'Ngày cuối cùng của tháng'
            if self.monthly_day:
                return f'Ngày {self.monthly_day} hàng tháng'
            if self.monthly_week and self.monthly_weekday is not None:
                return f'Thứ {self.monthly_weekday + 2 if self.monthly_weekday < 5 else 1} tuần thứ {self.monthly_week}'
            return 'Hàng tháng'
        if self.frequency == 'quarterly':
            return 'Hàng quý'
        if self.frequency == 'yearly':
            return 'Hàng năm'
        if self.frequency == 'custom':
            return f'Mỗi {self.custom_interval} {self.get_custom_interval_unit_display()}' if self.custom_interval and self.custom_interval_unit else 'Tùy chỉnh'
        return 'Không xác định'

    def is_due(self, today=None):
        today = today or timezone.now().date()
        if self.status != 'active':
            return False
        if self.end_date and today > self.end_date:
            return False
        if self.max_occurrences and self.occurrences >= self.max_occurrences:
            return False
        return self.next_run_date == today
'''
if not pattern.search(text):
    raise SystemExit('RecurringTransaction pattern not found!')
path.write_text(pattern.sub(new, text), encoding='utf-8')
