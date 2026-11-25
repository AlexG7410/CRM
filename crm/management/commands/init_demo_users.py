"""Create demo accounts: an admin/staff user and a customer panel user.

Run once after loading fixtures:
    python manage.py init_demo_users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from crm.models import Customer


class Command(BaseCommand):
    help = "حساب‌های نمایشی می‌سازد: مدیر سیستم و یک مشتری با دسترسی پنل"

    def handle(self, *args, **options):
        # Admin / staff account
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write(self.style.SUCCESS("✓ حساب مدیر: admin / admin123 (پنل مدیریت)"))

        # Customer panel account — link to the first customer
        customer = Customer.objects.first()
        if customer is None:
            self.stdout.write(self.style.WARNING("هیچ مشتری‌ای یافت نشد — ابتدا fixtures را بارگذاری کنید"))
            return
        cust_user, created = User.objects.get_or_create(
            username="customer1",
            defaults={"is_staff": False, "is_superuser": False},
        )
        cust_user.set_password("customer123")
        cust_user.is_staff = False
        cust_user.is_superuser = False
        cust_user.save()
        if customer.user is None:
            customer.user = cust_user
            customer.save()
        self.stdout.write(self.style.SUCCESS(
            f"✓ حساب مشتری: customer1 / customer123 (پنل مشتری) — متصل به «{customer.name}»"
        ))
        self.stdout.write(self.style.WARNING("\nآدرس پنل مشتری: http://127.0.0.1:8000/panel/login/"))
