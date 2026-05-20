from django.core.management.base import BaseCommand
from django.utils import timezone
from tracker.models import RecurringTransaction, Transaction


class Command(BaseCommand):
    help = 'Generate transactions from recurring transaction templates'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, help='Giới hạn cho một user cụ thể')

    def handle(self, *args, **options):
        today = timezone.now().date()
        recurring_txs = RecurringTransaction.objects.filter(is_active=True, status='active')

        if options.get('user_id'):
            recurring_txs = recurring_txs.filter(user_id=options['user_id'])

        total_created = 0

        for recurring in recurring_txs:
            # Kiểm tra đã hết hạn chưa
            if recurring.end_date and today > recurring.end_date:
                recurring.status = 'completed'
                recurring.is_active = False
                recurring.save()
                continue

            # Kiểm tra đã đủ số lần chưa
            if recurring.max_occurrences and recurring.occurrences >= recurring.max_occurrences:
                recurring.status = 'completed'
                recurring.is_active = False
                recurring.save()
                continue

            run_date = recurring.next_run_date or recurring.start_date
            if run_date < recurring.start_date:
                run_date = recurring.start_date

            while run_date and run_date <= today:
                # Kiểm tra end_date
                if recurring.end_date and run_date > recurring.end_date:
                    recurring.status = 'completed'
                    recurring.is_active = False
                    recurring.save()
                    break

                # Kiểm tra max occurrences
                if recurring.max_occurrences and recurring.occurrences >= recurring.max_occurrences:
                    recurring.status = 'completed'
                    recurring.is_active = False
                    recurring.save()
                    break

                # *** Chống tạo trùng: kiểm tra đã có giao dịch định kỳ này cho ngày này chưa ***
                already_exists = Transaction.objects.filter(
                    recurring=recurring,
                    date=run_date,
                ).exists()

                if not already_exists:
                    transaction_status = 'pending' if recurring.execution_mode == 'pending' else 'posted'
                    Transaction.objects.create(
                        user=recurring.user,
                        amount=recurring.amount,
                        type=recurring.type,
                        category=recurring.category,
                        date=run_date,
                        wallet=recurring.wallet,
                        notes=f'[Định kỳ] {recurring.notes}' if recurring.notes else '[Định kỳ]',
                        status=transaction_status,
                        recurring=recurring,
                    )
                    recurring.last_generated = run_date
                    recurring.occurrences += 1
                    total_created += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Tạo giao dịch: {recurring.category} ngày {run_date}'
                    ))

                # Tính ngày chạy tiếp theo
                next_run = recurring.compute_next_run_date(run_date)
                recurring.next_run_date = next_run

                if recurring.max_occurrences and recurring.occurrences >= recurring.max_occurrences:
                    recurring.status = 'completed'
                    recurring.is_active = False

                if recurring.end_date and next_run and next_run > recurring.end_date:
                    recurring.status = 'completed'
                    recurring.is_active = False

                recurring.save()
                run_date = next_run

        self.stdout.write(self.style.SUCCESS(
            f'\nHoàn tất: đã tạo {total_created} giao dịch định kỳ.'
        ))
