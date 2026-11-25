"""
Management command to seed the Wound Specialist CRM database
with realistic data covering ALL models.

Usage:
    python manage.py seed_all
    python manage.py seed_all --clear   # first delete existing data
"""

from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import (
    ActivityLog,
    Brand,
    ChatMessage,
    Commission,
    Consultation,
    Customer,
    DailyReport,
    Invoice,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductRequest,
    SatisfactionReview,
    WarehouseMovement,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with sample data covering all CRM models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing CRM data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            # ترتیب حذف مهم است (وابستگی‌ها)
            ActivityLog.objects.all().delete()
            ChatMessage.objects.all().delete()
            Commission.objects.all().delete()
            DailyReport.objects.all().delete()
            WarehouseMovement.objects.all().delete()
            ProductRequest.objects.all().delete()
            Payment.objects.all().delete()
            Invoice.objects.all().delete()
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            SatisfactionReview.objects.all().delete()
            Consultation.objects.all().delete()
            Customer.objects.all().delete()
            Product.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        self.stdout.write("Seeding data...")

        brands = self._seed_brands()
        products = self._seed_products(brands)
        customers = self._seed_customers()
        self._seed_consultations()
        self._seed_satisfaction(customers)
        orders, order_items = self._seed_orders(customers, products)
        invoices = self._seed_invoices(orders, customers)
        self._seed_payments(invoices, customers)
        self._seed_product_requests(customers, products)
        self._seed_warehouse_movements(products, orders)
        self._seed_daily_reports(customers)
        self._seed_commissions(customers, orders)
        self._seed_chat_messages(customers)
        self._seed_activity_logs()

        self.stdout.write(self.style.SUCCESS("Seeding completed successfully!"))

    # ------------------------------------------------------------------
    # BRANDS
    # ------------------------------------------------------------------
    def _seed_brands(self):
        data = [
            ("هارتمن", "آلمان", "🩹", "برند آلمانی پانسمان پیشرفته - از wounda.ir"),
            ("یوروفارم", "آلمان", "💊", "برند یوروفارم - از wounda.ir"),
            ("فاپسکو", "ایران", "🇮🇷", "برند ایرانی فاپسکو - از wounda.ir"),
            ("تریتا", "ایران", "🌿", "برند ایرانی تریتا - از wounda.ir"),
            ("زخمیران", "ایران", "🧬", "برند ایرانی زخمیران - از wounda.ir"),
        ]
        brands = {}
        for name, country, emoji, desc in data:
            brand, _ = Brand.objects.get_or_create(
                name=name,
                defaults={"country": country, "logo_emoji": emoji, "description": desc},
            )
            brands[name] = brand
        self.stdout.write(f"  → {len(brands)} brands")
        return brands

    # ------------------------------------------------------------------
    # PRODUCTS
    # ------------------------------------------------------------------
    def _seed_products(self, brands):
        data = [
            # (brand, name, category, wound_type, desc, price, stock, emoji, url)
            ("هارتمن", "پانسمان هیدروکل نازک هارتمن", "hydrocolloid", "all",
             "پانسمان هیدروکلوئیدی نازک برای زخم‌های سطحی", 285000, 145, "🩹",
             "https://wounda.ir/wp-content/uploads/hydrocol-thin.jpg"),
            ("هارتمن", "پانسمان آلژینات سوربالگون هارتمن", "alginate", "all",
             "پانسمان آلژینات برای زخم‌های با ترشح متوسط تا زیاد", 425000, 67, "🟦",
             "https://wounda.ir/wp-content/uploads/sorbalgon.jpg"),
            ("هارتمن", "پانسمان آلژینات کلسیم پرکننده سوربالگون", "alginate", "all",
             "پانسمان آلژینات کلسیم پرکننده برای حفره زخم", 510000, 38, "🟩",
             "https://wounda.ir/wp-content/uploads/sorbalgon-fill.jpg"),
            ("یوروفارم", "پانسمان استریل درپ یددار اینسیژن فیلم یورودرم", "transparent", "surgical",
             "پانسمان شفاف استریل برای زخم‌های جراحی", 365000, 92, "💎",
             "https://wounda.ir/wp-content/uploads/euroderm-incise.jpg"),
            ("هارتمن", "پانسمان جراحی آماده کاسموپور آنتی باکتریال", "surgical", "surgical",
             "پانسمان جراحی آنتی‌باکتریال آماده", 195000, 156, "🩹",
             "https://wounda.ir/wp-content/uploads/cosmopor-antibac.jpg"),
            ("هارتمن", "پانسمان جراحی پددار ضد آب هیدروفیلم پلاس", "surgical", "surgical",
             "پانسمان جراحی پددار ضد آب", 285000, 78, "🟦",
             "https://wounda.ir/wp-content/uploads/hydrofilm-plus.jpg"),
            ("هارتمن", "پانسمان زتوویت پلاس سیلیکون بوردر چسبدار", "foam", "all",
             "پانسمان فوم سیلیکونی با لبه چسبدار", 680000, 45, "🔷",
             "https://wounda.ir/wp-content/uploads/zetuvit-plus-silicone.jpg"),
            ("هارتمن", "پانسمان شفاف رولی هیدروفیلم هارتمن", "transparent", "all",
             "پانسمان شفاف رولی برای پوشش", 425000, 32, "💎",
             "https://wounda.ir/wp-content/uploads/hydrofilm-roll.jpg"),
            ("هارتمن", "پانسمان طبابرن", "silver", "chronic",
             "پانسمان حاوی نقره برای زخم‌های عفونی", 659000, 25, "✨",
             "https://wounda.ir/wp-content/uploads/tababern.jpg"),
            ("هارتمن", "پانسمان طبادرم", "hydrocolloid", "all",
             "پانسمان هیدروکلوئیدی طبادرم", 503000, 54, "🟦",
             "https://wounda.ir/wp-content/uploads/tabaderm.jpg"),
            ("هارتمن", "پانسمان طبادرم پلاس نقره", "silver", "chronic",
             "پانسمان هیدروکلوئیدی حاوی نقره", 621000, 41, "✨",
             "https://wounda.ir/wp-content/uploads/tabaderm-plus-silver.jpg"),
            ("هارتمن", "پانسمان طبافلکس", "foam", "all",
             "پانسمان فوم طبافلکس", 386000, 88, "🟦",
             "https://wounda.ir/wp-content/uploads/tabaflex.jpg"),
            ("هارتمن", "پانسمان طبافلکس پرو", "foam", "all",
             "پانسمان فوم حرفه‌ای طبافلکس پرو", 684000, 36, "🔷",
             "https://wounda.ir/wp-content/uploads/tabaflex-pro.jpg"),
            ("فاپسکو", "پانسمان کلاژن پودری فاپسکو", "collagen", "chronic",
             "پودر کلاژن برای زخم‌های مزمن", 890000, 22, "🧪",
             "https://wounda.ir/wp-content/uploads/fapsco-collagen.jpg"),
            ("تریتا", "پانسمان عسل تریتا", "honey", "chronic",
             "پانسمان حاوی عسل طبیعی برای زخم‌های آلوده", 475000, 58, "🍯",
             "https://wounda.ir/wp-content/uploads/tirita-honey.jpg"),
            ("زخمیران", "پانسمان هیدروژل زخمیران", "hydrogel", "all",
             "ژل آبرسان برای زخم‌های خشک", 245000, 73, "💧",
             "https://wounda.ir/wp-content/uploads/zakhamiran-hydrogel.jpg"),
        ]
        products = {}
        for brand_name, name, category, wound_type, desc, price, stock, emoji, url in data:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    "brand": brands[brand_name],
                    "category": category,
                    "wound_type": wound_type,
                    "description": desc,
                    "price": price,
                    "stock": stock,
                    "unit": "عدد",
                    "image_emoji": emoji,
                    "image_url": url,
                    "is_active": True,
                    "low_stock_threshold": 10,
                },
            )
            products[name] = product
        self.stdout.write(f"  → {len(products)} products")
        return products

    # ------------------------------------------------------------------
    # CUSTOMERS
    # ------------------------------------------------------------------
    def _seed_customers(self):
        data = [
            # (name, type, contact, phone, email, city, address, workplace, history, rate, status, notes)
            ("دکتر مریم احمدی", "wound_specialist", "دکتر مریم احمدی", "0912-345-6789",
             "ahmadi@woundcare.ir", "تهران", "تهران، خیابان ولیعصر",
             "کلینیک تخصصی زخم شفا", "۱۲ سال سابقه در درمان زخم‌های دیابتی و مزمن",
             20.00, "active", "متخصص زخم دیابتی"),
            ("کلینیک تخصصی زخم شفا", "wound_clinic", "دکتر احمدی", "021-2201-3344",
             "info@woundclinic-shafa.ir", "تهران", "تهران، خیابان ولیعصر، بالاتر از پارک‌وی",
             "کلینیک تخصصی زخم", "۸ سال فعالیت تخصصی", 20.00, "active", "کلینیک همکار اصلی"),
            ("بیمارستان دیابت ایران", "wound_hospital", "دکتر لاریجانی", "021-2288-4400",
             "info@diabet-iran.ir", "تهران", "تهران، خیابان فرشته",
             "بخش مراقبت ویژه دیابتی", "بخش تخصصی زخم دیابتی با ۸۰ تخت",
             20.00, "active", "بیمارستان اصلی همکار"),
            ("بیمارستان استاد مطهری", "wound_hospital", "دکتر اکبری", "051-3840-1122",
             "info@motahari-hospital.ir", "مشهد", "مشهد، بلوار وکیل‌آباد",
             "بخش جراحی و زخم", "۱۰۰ تخت فعال بخش زخم", 20.00, "active", ""),
            ("داروخانه ۲۴ ساعته شفایاب", "pharmacy", "آقای رضایی", "021-3344-5566",
             "", "تهران", "تهران، میدان انقلاب", "داروخانه",
             "۵ سال فعالیت در فروش محصولات زخم", 20.00, "active", "داروخانه همکار"),
            ("کلینیک دیابت البرز", "diabetes_clinic", "دکتر صادقی", "026-3222-1100",
             "info@alborz-diabetes.ir", "کرج", "کرج، بلوار طالقانی",
             "کلینیک تخصصی دیابت", "۷ سال فعالیت در مراقبت از پای دیابتی",
             20.00, "active", "کلینیک دیابت همکار"),
            ("دکتر رضا کریمی", "infectious_doctor", "دکتر رضا کریمی", "0913-222-1111",
             "karimi@woundcare.ir", "تهران", "تهران، خیابان شریعتی",
             "بیمارستان امیرالمؤمنین", "۸ سال سابقه در بیماری‌های عفونی و زخم‌های عفونی",
             20.00, "active", "متخصص بیماری‌های عفونی"),
            ("دکتر سحر نوری", "wound_specialist", "دکتر سحر نوری", "0911-888-9999",
             "nouri@woundcare.ir", "اصفهان", "اصفهان، خیابان چهارباغ",
             "مرکز درمانی سبز", "۱۴ سال سابقه در دبریدمان و ترمیم زخم",
             20.00, "active", "متخصص طب فیزیکی و ترمیم"),
            ("دکتر حسین موسوی", "wound_specialist", "دکتر حسین موسوی", "0915-111-2233",
             "mousavi@woundcare.ir", "شیراز", "شیراز، بلوار زند",
             "درمانگاه زخم شیراز", "۶ سال سابقه", 18.00, "prospect",
             "در حال مذاکره برای همکاری"),
            ("داروخانه مرکزی تبریز", "pharmacy", "آقای حسینی", "041-3300-4455",
             "", "تبریز", "تبریز، خیابان امام", "داروخانه", "",
             20.00, "inactive", "همکاری متوقف شده"),
        ]
        customers = {}
        for row in data:
            (name, ctype, contact, phone, email, city, address,
             workplace, history, rate, status, notes) = row
            customer, _ = Customer.objects.get_or_create(
                name=name,
                defaults={
                    "type": ctype,
                    "contact_person": contact,
                    "phone": phone,
                    "email": email,
                    "city": city,
                    "address": address,
                    "workplace": workplace,
                    "work_history": history,
                    "commission_rate": rate,
                    "status": status,
                    "notes": notes,
                },
            )
            customers[name] = customer
        self.stdout.write(f"  → {len(customers)} customers")
        return customers

    # ------------------------------------------------------------------
    # CONSULTATIONS
    # ------------------------------------------------------------------
    def _seed_consultations(self):
        data = [
            ("خانم رضایی", "0912-000-1111", "diabetic",
             "زخم پای دیابتی دارم، چه پانسمانی مناسب است؟",
             "", "", "pending", None),
            ("آقای محمدی", "0913-000-2222", "pressure",
             "زخم بستر در ناحیه ساکرال، پانسمان فوم بهتر است یا هیدروکلوئید؟",
             "برای زخم بستر با ترشح متوسط، پانسمان فوم سیلیکونی توصیه می‌شود.",
             "دکتر مریم احمدی", "answered", timezone.now() - timedelta(days=2)),
            ("خانم کریمی", "0914-000-3333", "burn",
             "سوختگی درجه دو در دست، چه پانسمانی مناسب است؟",
             "پانسمان هیدروژل یا فوم ضدچسبندگی توصیه می‌شود.",
             "دکتر سحر نوری", "closed", timezone.now() - timedelta(days=5)),
        ]
        count = 0
        for name, phone, wtype, question, answer, answered_by, status, answered_at in data:
            _, created = Consultation.objects.get_or_create(
                customer_name=name,
                question=question,
                defaults={
                    "phone": phone,
                    "wound_type": wtype,
                    "answer": answer,
                    "answered_by": answered_by,
                    "status": status,
                    "answered_at": answered_at,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} consultations")

    # ------------------------------------------------------------------
    # SATISFACTION
    # ------------------------------------------------------------------
    def _seed_satisfaction(self, customers):
        data = [
            ("دکتر مریم احمدی", 5, "کیفیت محصولات و پشتیبانی عالی بود.", 5, 5, 4),
            ("کلینیک تخصصی زخم شفا", 4, "تحویل کمی دیر شد ولی کیفیت خوب بود.", 5, 4, 3),
            ("بیمارستان دیابت ایران", 5, "همکاری بسیار رضایت‌بخش.", 5, 5, 5),
            ("داروخانه ۲۴ ساعته شفایاب", 4, "قیمت مناسب، بسته‌بندی خوب.", 4, 4, 4),
        ]
        count = 0
        for name, rating, comment, pq, sq, ds in data:
            _, created = SatisfactionReview.objects.get_or_create(
                customer=customers[name],
                comment=comment,
                defaults={
                    "rating": rating,
                    "product_quality": pq,
                    "service_quality": sq,
                    "delivery_speed": ds,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} satisfaction reviews")

    # ------------------------------------------------------------------
    # ORDERS + ORDER ITEMS
    # ------------------------------------------------------------------
    def _seed_orders(self, customers, products):
        orders_data = [
            # (customer_name, status, payment_status, notes, items[(product_name, qty)])
            ("دکتر مریم احمدی", "delivered", "paid", "سفارش نمونه اول",
             [("پانسمان هیدروکل نازک هارتمن", 2), ("پانسمان زتوویت پلاس سیلیکون بوردر چسبدار", 1)]),
            ("کلینیک تخصصی زخم شفا", "shipped", "partial", "سفارش کلینیک شفا",
             [("پانسمان آلژینات سوربالگون هارتمن", 3), ("پانسمان طبافلکس", 2)]),
            ("بیمارستان دیابت ایران", "pending", "unpaid", "",
             [("پانسمان استریل درپ یددار اینسیژن فیلم یورودرم", 5)]),
            ("داروخانه ۲۴ ساعته شفایاب", "in_warehouse", "unpaid", "در انتظار آماده‌سازی",
             [("پانسمان عسل تریتا", 4)]),
            ("بیمارستان استاد مطهری", "confirmed_received", "paid", "سفارش تکمیل شده",
             [("پانسمان طبادرم پلاس نقره", 3), ("پانسمان طبابرن", 2)]),
        ]
        orders = {}
        order_items = []
        for customer_name, status, pay_status, notes, items in orders_data:
            customer = customers[customer_name]
            order = Order.objects.create(
                customer=customer,
                status=status,
                payment_status=pay_status,
                notes=notes,
            )
            orders[customer_name] = order
            for product_name, qty in items:
                product = products[product_name]
                item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    unit_price=product.price,
                )
                order_items.append(item)
        self.stdout.write(f"  → {len(orders)} orders, {len(order_items)} order items")
        return orders, order_items

    # ------------------------------------------------------------------
    # INVOICES
    # ------------------------------------------------------------------
    def _seed_invoices(self, orders, customers):
        invoices = {}
        # برای هر سفارش یک پیش‌فاکتور + برای بعضی فاکتور نهایی
        for customer_name, order in orders.items():
            customer = customers[customer_name]
            amount = order.subtotal
            pre = Invoice.objects.create(
                order=order,
                customer=customer,
                type=Invoice.TypeChoices.PRE_INVOICE,
                amount=amount,
                status=Invoice.StatusChoices.ISSUED,
                notes=f"پیش‌فاکتور سفارش {order.number}",
            )
            invoices[(customer_name, "pre")] = pre

            if order.status in ("delivered", "confirmed_received"):
                final = Invoice.objects.create(
                    order=order,
                    customer=customer,
                    type=Invoice.TypeChoices.INVOICE,
                    amount=amount,
                    status=Invoice.StatusChoices.PAID,
                    notes=f"فاکتور نهایی سفارش {order.number}",
                )
                invoices[(customer_name, "final")] = final
            elif order.status == "shipped":
                final = Invoice.objects.create(
                    order=order,
                    customer=customer,
                    type=Invoice.TypeChoices.INVOICE,
                    amount=amount,
                    status=Invoice.StatusChoices.SENT_WITH_RECEIPT,
                    notes=f"فاکتور سفارش {order.number}",
                )
                invoices[(customer_name, "final")] = final
        self.stdout.write(f"  → {len(invoices)} invoices")
        return invoices

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------
    def _seed_payments(self, invoices, customers):
        count = 0
        for (customer_name, kind), invoice in invoices.items():
            customer = customers[customer_name]
            if kind == "final" and invoice.status == Invoice.StatusChoices.PAID:
                Payment.objects.create(
                    invoice=invoice,
                    customer=customer,
                    amount=invoice.total,
                    method=Payment.MethodChoices.TRANSFER,
                    status=Payment.StatusChoices.CONFIRMED,
                    transaction_ref=f"TRX-{invoice.id:06d}",
                    notes="پرداخت کامل",
                )
                count += 1
            elif kind == "final" and invoice.status == Invoice.StatusChoices.SENT_WITH_RECEIPT:
                # پرداخت جزئی + چک در انتظار
                Payment.objects.create(
                    invoice=invoice,
                    customer=customer,
                    amount=int(invoice.total * 0.5),
                    method=Payment.MethodChoices.CARD,
                    status=Payment.StatusChoices.CONFIRMED,
                    transaction_ref=f"TRX-{invoice.id:06d}A",
                    notes="پرداخت علی‌الحساب",
                )
                Payment.objects.create(
                    invoice=invoice,
                    customer=customer,
                    amount=invoice.total - int(invoice.total * 0.5),
                    method=Payment.MethodChoices.CHEQUE,
                    status=Payment.StatusChoices.PENDING,
                    transaction_ref="",
                    notes="چک در انتظار وصول",
                )
                count += 2
        self.stdout.write(f"  → {count} payments")

    # ------------------------------------------------------------------
    # PRODUCT REQUESTS
    # ------------------------------------------------------------------
    def _seed_product_requests(self, customers, products):
        data = [
            ("کلینیک دیابت البرز", "پانسمان فوم سیلیکونی",
             "پانسمان زتوویت پلاس سیلیکون بوردر چسبدار", 10,
             "برای بیماران کلینیک دیابت", "sent_to_finance"),
            ("بیمارستان استاد مطهری", "پانسمان نقره",
             "پانسمان طبادرم پلاس نقره", 20,
             "نیاز بخش زخم بیمارستان", "in_warehouse"),
            ("دکتر رضا کریمی", "پودر کلاژن",
             "پانسمان کلاژن پودری فاپسکو", 5,
             "برای بیماران عفونی", "pending"),
            ("دکتر سحر نوری", "پانسمان هیدروژل",
             "پانسمان هیدروژل زخمیران", 8,
             "برای زخم‌های خشک", "completed"),
        ]
        count = 0
        for customer_name, product_name, product_ref, qty, notes, status in data:
            _, created = ProductRequest.objects.get_or_create(
                customer=customers[customer_name],
                product_name=product_name,
                defaults={
                    "product": products[product_ref],
                    "quantity": qty,
                    "unit": "عدد",
                    "notes": notes,
                    "status": status,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} product requests")

    # ------------------------------------------------------------------
    # WAREHOUSE MOVEMENTS
    # ------------------------------------------------------------------
    def _seed_warehouse_movements(self, products, orders):
        data = [
            # (type, product_name, qty, reason, reference, order_customer, operator, notes)
            ("in", "پانسمان هیدروکل نازک هارتمن", 100, "purchase", "PO-1001", None,
             "انباردار علی", "خرید اولیه"),
            ("out", "پانسمان هیدروکل نازک هارتمن", 2, "order_delivery", "ORD-0001",
             "دکتر مریم احمدی", "انباردار علی", "تحویل سفارش ۱"),
            ("out", "پانسمان آلژینات سوربالگون هارتمن", 3, "order_delivery", "ORD-0002",
             "کلینیک تخصصی زخم شفا", "انباردار رضا", "تحویل سفارش ۲"),
            ("in", "پانسمان زتوویت پلاس سیلیکون بوردر چسبدار", 20, "return", "RET-2001",
             None, "انباردار علی", "مرجوعی از کلینیک"),
            ("out", "پانسمان عسل تریتا", 1, "damage", "DMG-3001", None,
             "انباردار رضا", "ضایعات"),
            ("in", "پانسمان طبافلکس", 50, "purchase", "PO-1002", None,
             "انباردار علی", "خرید مکمل"),
        ]
        count = 0
        for mtype, product_name, qty, reason, ref, order_customer, operator, notes in data:
            _, created = WarehouseMovement.objects.get_or_create(
                type=mtype,
                product=products[product_name],
                quantity=qty,
                reason=reason,
                reference=ref,
                defaults={
                    "order": orders.get(order_customer) if order_customer else None,
                    "operator": operator,
                    "notes": notes,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} warehouse movements")

    # ------------------------------------------------------------------
    # DAILY REPORTS
    # ------------------------------------------------------------------
    def _seed_daily_reports(self, customers):
        today = date.today()
        data = [
            ("علی محمدی", today - timedelta(days=1), "visit", "دکتر مریم احمدی",
             3, 5, 4, 1, 1250000, "ویزیت موفق در کلینیک شفا"),
            ("علی محمدی", today, "presentation", "کلینیک تخصصی زخم شفا",
             1, 8, 6, 0, 0, "ارائه پرزنت محصولات جدید"),
            ("سارا رحیمی", today, "follow_up", "دکتر حسین موسوی",
             0, 4, 0, 1, 0, "پیگیری مشتری بالقوه"),
            ("سارا رحیمی", today - timedelta(days=2), "call", "داروخانه ۲۴ ساعته شفایاب",
             0, 10, 3, 0, 950000, "تماس‌های فروش"),
        ]
        count = 0
        for presenter, rdate, atype, customer_name, visits, calls, presented, new_c, sales, notes in data:
            _, created = DailyReport.objects.get_or_create(
                presenter_name=presenter,
                report_date=rdate,
                activity_type=atype,
                customer=customers[customer_name],
                defaults={
                    "visits_count": visits,
                    "calls_count": calls,
                    "products_presented": presented,
                    "new_customers": new_c,
                    "sales_amount": sales,
                    "notes": notes,
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} daily reports")

    # ------------------------------------------------------------------
    # COMMISSIONS
    # ------------------------------------------------------------------
    def _seed_commissions(self, customers, orders):
        count = 0
        for customer_name, order in orders.items():
            customer = customers[customer_name]
            base = order.subtotal
            if base == 0:
                continue
            status = Commission.StatusChoices.PENDING
            paid_at = None
            if order.status in ("delivered", "confirmed_received"):
                status = Commission.StatusChoices.PAID
                paid_at = timezone.now() - timedelta(days=1)
            elif order.status == "shipped":
                status = Commission.StatusChoices.APPROVED
            commission, created = Commission.objects.get_or_create(
                customer=customer,
                order=order,
                defaults={
                    "rate": customer.commission_rate,
                    "base_amount": base,
                    "status": status,
                    "paid_at": paid_at,
                    "notes": f"پورسانت سفارش {order.number}",
                },
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} commissions")

    # ------------------------------------------------------------------
    # CHAT MESSAGES
    # ------------------------------------------------------------------
    def _seed_chat_messages(self, customers):
        data = [
            ("دکتر مریم احمدی", "سلام، موجودی پانسمان هیدروکل نازک چقدر است؟", True, True),
            ("دکتر مریم احمدی", "سلام، موجودی ۱۴۵ عدد است و آماده ارسال.", False, True),
            ("کلینیک تخصصی زخم شفا", "لطفاً پیش‌فاکتور سفارش دوم را ارسال کنید.", True, False),
            ("دکتر حسین موسوی", "برای همکاری نیاز به کاتالوگ محصولات داریم.", True, False),
            ("داروخانه ۲۴ ساعته شفایاب", "سفارش جدید ثبت شد، لطفاً تأیید کنید.", True, False),
        ]
        count = 0
        for customer_name, message, from_customer, read in data:
            _, created = ChatMessage.objects.get_or_create(
                customer=customers[customer_name],
                message=message,
                defaults={"from_customer": from_customer, "read": read},
            )
            if created:
                count += 1
        self.stdout.write(f"  → {count} chat messages")

    # ------------------------------------------------------------------
    # ACTIVITY LOGS
    # ------------------------------------------------------------------
        # ------------------------------------------------------------------
    # ACTIVITY LOGS
    # ------------------------------------------------------------------
    def _seed_activity_logs(self):
        # اگر قبلاً لاگی وجود دارد، دوباره نساز
        if ActivityLog.objects.exists():
            self.stdout.write(f"  → activity logs already exist ({ActivityLog.objects.count()}), skipping")
            return

        admin = User.objects.filter(username="admin").first()
        data = [
            (admin, "admin", "login", "auth", "ورود به سیستم",
             "", "", "192.168.1.10", "Mozilla/5.0"),
            (admin, "admin", "create", "orders", "ایجاد سفارش ORD-0001",
             "1", "ORD-0001", "192.168.1.10", "Mozilla/5.0"),
            (admin, "operator1", "payment", "payments",
             "ثبت پرداخت برای فاکتور", "1", "TRX-000001",
             "192.168.1.11", "Mozilla/5.0"),
            (admin, "operator1", "report", "daily_reports",
             "ثبت گزارش روزانه", "1", "علی محمدی", "192.168.1.11", "Mozilla/5.0"),
            (admin, "admin", "export", "reports", "خروجی اکسل گزارش فروش",
             "", "", "192.168.1.10", "Mozilla/5.0"),
            (admin, "operator1", "view", "customers", "مشاهده لیست مشتریان",
             "", "", "192.168.1.11", "Mozilla/5.0"),
        ]
        count = 0
        for user, user_name, action, module, desc, oid, orepr, ip, ua in data:
            ActivityLog.objects.create(
                user=user,
                user_name=user_name,
                action=action,
                module=module,
                description=desc,
                object_id=oid,
                object_repr=orepr,
                ip_address=ip,
                user_agent=ua,
            )
            count += 1
        self.stdout.write(f"  → {count} activity logs")