"""
Models for the Wound Specialist CRM (APP CRM متخصص)
Project: CRM for wound care clinics and product sales
Based on wounda.ir product catalog
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings


# ====================================================================
# CUSTOMER (مشتریان)
# ====================================================================
class Customer(models.Model):
    """Customer with multiple types: wound specialist, clinic, hospital, pharmacy, etc."""

    class TypeChoices(models.TextChoices):
        WOUND_SPECIALIST = "wound_specialist", _("زخم‌کار")
        WOUND_CLINIC = "wound_clinic", _("کلینیک زخم")
        WOUND_HOSPITAL = "wound_hospital", _("بیمارستان دارای بخش زخم")
        PHARMACY = "pharmacy", _("داروخانه")
        DIABETES_CLINIC = "diabetes_clinic", _("کلینیک دیابت")
        INFECTIOUS_DOCTOR = "infectious_doctor", _("پزشک داخلی عفونی")

    class StatusChoices(models.TextChoices):
        ACTIVE = "active", _("فعال")
        INACTIVE = "inactive", _("غیرفعال")
        PROSPECT = "prospect", _("مشتری بالقوه")

    name = models.CharField(_("نام"), max_length=200)
    type = models.CharField(_("نوع مشتری"), max_length=30, choices=TypeChoices.choices)
    contact_person = models.CharField(_("نام فرد قابل تماس"), max_length=150, blank=True)
    phone = models.CharField(_("شماره تماس"), max_length=20)
    email = models.EmailField(_("ایمیل"), blank=True)
    city = models.CharField(_("شهر"), max_length=50, blank=True)
    address = models.TextField(_("آدرس"), blank=True)
    # For wound specialists
    workplace = models.CharField(_("محل کار فعلی"), max_length=200, blank=True)
    work_history = models.TextField(_("سابقه کاری"), blank=True, help_text="سابقه کاری زخم‌کار")
    # Commission rate (default 20%)
    commission_rate = models.DecimalField(
        _("درصد پورسانت"),
        max_digits=5,
        decimal_places=2,
        default=20.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    notes = models.TextField(_("یادداشت"), blank=True)
    # Linked Django auth user for customer panel access (nullable)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_profile",
        verbose_name=_("حساب کاربری پنل"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("مشتری")
        verbose_name_plural = _("مشتریان")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_spent(self):
        return sum(o.total for o in self.orders.all() if o.total)

    @property
    def total_commission(self):
        """Total commission earned by this customer."""
        return sum(o.commission_amount for o in self.orders.all() if o.commission_amount)


# ====================================================================
# PRODUCT (محصولات) - Based on wounda.ir catalog
# ====================================================================
class Brand(models.Model):
    """Product brand/manufacturer."""
    name = models.CharField(_("نام برند"), max_length=100, unique=True)
    country = models.CharField(_("کشور سازنده"), max_length=50, blank=True)
    logo_emoji = models.CharField(_("آیکون"), max_length=10, default="🏷️")
    description = models.TextField(_("توضیحات"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("برند")
        verbose_name_plural = _("برندها")
        ordering = ["name"]

    def __str__(self):
        return f"{self.logo_emoji} {self.name}"

    @property
    def product_count(self):
        return self.products.count()


class Product(models.Model):
    """Wound care product from wounda.ir catalog."""

    class CategoryChoices(models.TextChoices):
        HYDROCOLOID = "hydrocolloid", _("پانسمان هیدروکلوئید")
        FOAM = "foam", _("پانسمان فوم")
        ALGINATE = "alginate", _("پانسمان آلژینات")
        SILVER = "silver", _("پانسمان نقره")
        PHMB = "phmb", _("پانسمان PHMB")
        HYDROGEL = "hydrogel", _("پانسمان هیدروژل")
        HYDROFIBER = "hydrofiber", _("پانسمان هیدروفایبر")
        COLLAGEN = "collagen", _("پانسمان کلاژن")
        HONEY = "honey", _("پانسمان عسل")
        ABSORBENT = "absorbent", _("پانسمان جاذب")
        SURGICAL = "surgical", _("پانسمان جراحی")
        TRANSPARENT = "transparent", _("پانسمان شفاف")
        SACRAL = "sacral", _("پانسمان ساکرال")
        NPWT = "npwt", _("وکیوم تراپی")
        HEEL = "heel", _("پانسمان پاشنه")
        TRACHEOSTOMY = "tracheostomy", _("پانسمان تراکئوستومی")
        DEBRIDEMENT = "debridement", _("دبرید")
        HEALING = "healing", _("ترمیم کننده")
        ADHESIVE = "adhesive", _("چسب پانسمان")
        CONCAVE = "concave", _("پانسمان کانکیو")
        OTHER = "other", _("سایر")

    class WoundType(models.TextChoices):
        DIABETIC = "diabetic", _("زخم دیابتی")
        PRESSURE = "pressure", _("زخم بستر")
        VENOUS = "venous", _("زخم وریدی")
        ARTERIAL = "arterial", _("زخم شریانی")
        SURGICAL = "surgical", _("زخم جراحی")
        BURN = "burn", _("زخم سوختگی")
        TRAUMA = "trauma", _("زخم تروماتیک")
        CHRONIC = "chronic", _("زخم مزمن")
        ACUTE = "acute", _("زخم حاد")
        ALL = "all", _("همه زخم‌ها")

    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("برند"),
    )
    name = models.CharField(_("نام محصول"), max_length=300)
    category = models.CharField(
        _("دسته‌بندی"),
        max_length=30,
        choices=CategoryChoices.choices,
        default=CategoryChoices.OTHER,
    )
    wound_type = models.CharField(
        _("نوع زخم"),
        max_length=20,
        choices=WoundType.choices,
        default=WoundType.ALL,
    )
    description = models.TextField(_("توضیحات"), blank=True)
    price = models.PositiveIntegerField(_("قیمت (تومان)"), validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(_("موجودی انبار"), default=0, validators=[MinValueValidator(0)])
    unit = models.CharField(_("واحد"), max_length=20, default="عدد")
    image_emoji = models.CharField(_("آیکون"), max_length=10, default="🩹")
    image_url = models.URLField(_("URL تصویر"), blank=True, help_text="آدرس تصویر محصول از wounda.ir")
    image = models.ImageField(_("تصویر محصول"), upload_to="products/", blank=True, null=True)
    is_active = models.BooleanField(_("فعال"), default=True)
    low_stock_threshold = models.PositiveIntegerField(_("آستان هشدار موجودی کم"), default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("محصول")
        verbose_name_plural = _("محصولات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["brand"]),
            models.Index(fields=["category"]),
            models.Index(fields=["wound_type"]),
        ]

    def __str__(self):
        return f"{self.image_emoji} {self.name} ({self.brand.name})"

    @property
    def total_value(self):
        return self.stock * self.price

    @property
    def is_low_stock(self):
        return self.stock < self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.stock == 0


# ====================================================================
# ONLINE CONSULTATION (مشاوره آنلاین)
# ====================================================================
class Consultation(models.Model):
    """Online wound care consultation request."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", _("در انتظار پاسخ")
        ANSWERED = "answered", _("پاسخ داده شده")
        CLOSED = "closed", _("بسته شده")

    class WoundTypeChoices(models.TextChoices):
        DIABETIC = "diabetic", _("زخم دیابتی")
        PRESSURE = "pressure", _("زخم بستر")
        VENOUS = "venous", _("زخم وریدی")
        SURGICAL = "surgical", _("زخم جراحی")
        BURN = "burn", _("سوختگی")
        OTHER = "other", _("سایر")

    customer_name = models.CharField(_("نام مراجع"), max_length=200)
    phone = models.CharField(_("شماره تماس"), max_length=20)
    # Linked customer (for logged-in panel users); keeps customer_name/phone for anonymous
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultations",
        verbose_name=_("مشتری"),
    )
    wound_type = models.CharField(
        _("نوع زخم"),
        max_length=20,
        choices=WoundTypeChoices.choices,
        default=WoundTypeChoices.OTHER,
    )
    question = models.TextField(_("سوال/شرح حال"))
    answer = models.TextField(_("پاسخ متخصص"), blank=True)
    answered_by = models.CharField(_("پاسخ‌دهنده"), max_length=150, blank=True)
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("مشاوره آنلاین")
        verbose_name_plural = _("مشاوره‌های آنلاین")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_name} - {self.get_wound_type_display()}"


# ====================================================================
# CUSTOMER SATISFACTION (رضایت مندی)
# ====================================================================
class SatisfactionReview(models.Model):
    """Customer satisfaction review/rating."""

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("مشتری"),
    )
    rating = models.PositiveIntegerField(
        _("امتیاز"),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(_("نظر مشتری"), blank=True)
    product_quality = models.PositiveIntegerField(
        _("کیفیت محصولات"),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    service_quality = models.PositiveIntegerField(
        _("کیفیت خدمات"),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    delivery_speed = models.PositiveIntegerField(
        _("سرعت تحویل"),
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("رضایت‌سنجی")
        verbose_name_plural = _("رضایت‌سنجی‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name} - {self.rating} ستاره"


# ====================================================================
# ORDER & ORDER ITEM (سفارش و آیتم‌ها)
# ====================================================================
class Order(models.Model):
    """Customer order with workflow tracking."""

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", _("پیش‌نویس")
        PENDING = "pending", _("در انتظار")
        SENT_TO_FINANCE = "sent_to_finance", _("ارسال به مسئول مالی")
        PRE_INVOICE_ISSUED = "pre_invoice_issued", _("صدور پیش فاکتور")
        INVOICE_APPROVED = "invoice_approved", _("تأیید فاکتور")
        INVOICE_ISSUED = "invoice_issued", _("صدور فاکتور")
        SENT_TO_PROCUREMENT = "sent_to_procurement", _("ارسال به تدارکات")
        IN_WAREHOUSE = "in_warehouse", _("در انبار")
        SHIPPED = "shipped", _("ارسال شده")
        DELIVERED = "delivered", _("تحویل به مشتری")
        CONFIRMED_RECEIVED = "confirmed_received", _("تأیید دریافت کالا")
        CANCELLED = "cancelled", _("لغو شده")

    class PaymentStatusChoices(models.TextChoices):
        UNPAID = "unpaid", _("پرداخت نشده")
        PARTIAL = "partial", _("پرداخت جزئی")
        PAID = "paid", _("پرداخت شده")
        REFUNDED = "refunded", _("بازگشت داده شده")

    number = models.CharField(_("شماره سفارش"), max_length=20, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("مشتری"),
    )
    status = models.CharField(
        _("وضعیت سفارش"),
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    payment_status = models.CharField(
        _("وضعیت پرداخت"),
        max_length=20,
        choices=PaymentStatusChoices.choices,
        default=PaymentStatusChoices.UNPAID,
    )
    notes = models.TextField(_("یادداشت"), blank=True)
    # Commission tracking
    commission_amount = models.PositiveIntegerField(_("مبلغ پورسانت"), default=0)
    # Receipt upload for payment confirmation
    payment_receipt = models.ImageField(_("فیش واریزی"), upload_to="receipts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("سفارش")
        verbose_name_plural = _("سفارش‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} - {self.customer.name}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def tax(self):
        return int(self.subtotal * 0.1)

    @property
    def total(self):
        return self.subtotal + self.tax

    @property
    def calculated_commission(self):
        """Calculate commission based on customer's rate."""
        if not self.commission_amount:
            rate = float(self.customer.commission_rate) / 100
            return int(self.subtotal * rate)
        return self.commission_amount

    def save(self, *args, **kwargs):
        if not self.number:
            last = Order.objects.order_by("-id").first()
            next_num = (last.id + 1) if last else 1
            self.number = f"ORD-{next_num:04d}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Order line item."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("سفارش"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("محصول"),
    )
    quantity = models.PositiveIntegerField(_("تعداد"), default=1, validators=[MinValueValidator(1)])
    unit_price = models.PositiveIntegerField(_("قیمت واحد"), default=0)

    class Meta:
        verbose_name = _("آیتم سفارش")
        verbose_name_plural = _("آیتم‌های سفارش")

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)


# ====================================================================
# INVOICE (فاکتور)
# ====================================================================
class Invoice(models.Model):
    """Invoice linked to an order."""

    class TypeChoices(models.TextChoices):
        PRE_INVOICE = "pre_invoice", _("پیش فاکتور")
        INVOICE = "invoice", _("فاکتور")

    class StatusChoices(models.TextChoices):
        DRAFT = "draft", _("پیش‌نویس")
        SENT_FOR_APPROVAL = "sent_for_approval", _("ارسال برای تأیید")
        APPROVED = "approved", _("تأیید شده")
        ISSUED = "issued", _("صدور شده")
        SENT_WITH_RECEIPT = "sent_with_receipt", _("ارسال با فیش واریزی")
        PAID = "paid", _("پرداخت شده")
        OVERDUE = "overdue", _("سررسید گذشته")

    number = models.CharField(_("شماره فاکتور"), max_length=30, unique=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name=_("سفارش"),
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name=_("مشتری"),
    )
    type = models.CharField(_("نوع"), max_length=20, choices=TypeChoices.choices)
    amount = models.PositiveIntegerField(_("مبلغ پایه"), default=0)
    tax = models.PositiveIntegerField(_("مالیات"), default=0)
    total = models.PositiveIntegerField(_("مبلغ نهایی"), default=0)
    status = models.CharField(
        _("وضعیت"),
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    issue_date = models.DateField(_("تاریخ صدور"), null=True, blank=True)
    due_date = models.DateField(_("تاریخ سررسید"), null=True, blank=True)
    notes = models.TextField(_("یادداشت"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("فاکتور")
        verbose_name_plural = _("فاکتورها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if not self.number:
            last = Invoice.objects.order_by("-id").first()
            next_num = (last.id + 1) if last else 1
            prefix = "PRE" if self.type == self.TypeChoices.PRE_INVOICE else "INV"
            self.number = f"{prefix}-1403-{next_num:04d}"
        if self.amount and not self.tax:
            self.tax = int(self.amount * 0.1)
        if self.amount and not self.total:
            self.total = self.amount + self.tax
        super().save(*args, **kwargs)


# ====================================================================
# PAYMENT (پرداخت)
# ====================================================================
class Payment(models.Model):
    """Payment record."""

    class MethodChoices(models.TextChoices):
        CARD = "card", _("کارت بانکی")
        TRANSFER = "transfer", _("انتقال بانکی")
        CASH = "cash", _("نقدی")
        CHEQUE = "cheque", _("چک")
        POS = "pos", _("پوز")

    class StatusChoices(models.TextChoices):
        CONFIRMED = "confirmed", _("تأیید شد")
        PENDING = "pending", _("در انتظار")
        FAILED = "failed", _("ناموفق")

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("فاکتور"),
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("مشتری"),
    )
    amount = models.PositiveIntegerField(_("مبلغ"), validators=[MinValueValidator(1)])
    method = models.CharField(_("روش پرداخت"), max_length=20, choices=MethodChoices.choices)
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    transaction_ref = models.CharField(_("کد تراکنش"), max_length=100, blank=True)
    receipt_image = models.ImageField(_("تصویر فیش"), upload_to="payments/", blank=True, null=True)
    notes = models.TextField(_("یادداشت"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("پرداخت")
        verbose_name_plural = _("پرداخت‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name} - {self.amount:,}"


# ====================================================================
# PRODUCT REQUEST (فرم درخواست محصول از مشتری)
# ====================================================================
class ProductRequest(models.Model):
    """Customer request for a product."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", _("در انتظار")
        SENT_TO_FINANCE = "sent_to_finance", _("ارسال به مسئول مالی")
        PRE_INVOICE_ISSUED = "pre_invoice_issued", _("صدور پیش فاکتور")
        IN_WAREHOUSE = "in_warehouse", _("در انبار")
        SENT_TO_PROCUREMENT = "sent_to_procurement", _("ارسال به تدارکات")
        IN_PROGRESS = "in_progress", _("در دست اقدام")
        COMPLETED = "completed", _("تکمیل شده")
        CANCELLED = "cancelled", _("لغو شده")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="product_requests",
        verbose_name=_("مشتری"),
    )
    product_name = models.CharField(_("نام محصول"), max_length=300)
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
        verbose_name=_("محصول مرتبط"),
    )
    quantity = models.PositiveIntegerField(_("تعداد"), validators=[MinValueValidator(1)])
    unit = models.CharField(_("واحد"), max_length=20, default="عدد")
    notes = models.TextField(_("توضیحات مشتری"), blank=True)
    status = models.CharField(
        _("وضعیت"),
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    # Tracking which department handled it
    sent_to_finance_at = models.DateTimeField(null=True, blank=True)
    sent_to_warehouse_at = models.DateTimeField(null=True, blank=True)
    sent_to_procurement_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("درخواست محصول")
        verbose_name_plural = _("درخواست‌های محصول")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name} - {self.product_name} × {self.quantity}"


# ====================================================================
# WAREHOUSE MOVEMENT (خروج/ورود انبار)
# ====================================================================
class WarehouseMovement(models.Model):
    """Warehouse entry/exit record."""

    class TypeChoices(models.TextChoices):
        IN = "in", _("ورودی")
        OUT = "out", _("خروجی")
        TRANSFER = "transfer", _("انتقال")

    class ReasonChoices(models.TextChoices):
        PURCHASE = "purchase", _("خرید")
        ORDER_DELIVERY = "order_delivery", _("تحویل سفارش")
        RETURN = "return", _("مرجوع")
        ADJUSTMENT = "adjustment", _("تعدیل")
        DAMAGE = "damage", _("ضایعات")
        OTHER = "other", _("سایر")

    type = models.CharField(_("نوع"), max_length=10, choices=TypeChoices.choices)
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name=_("محصول"),
    )
    quantity = models.PositiveIntegerField(_("تعداد"), validators=[MinValueValidator(1)])
    reason = models.CharField(
        _("دلیل"),
        max_length=20,
        choices=ReasonChoices.choices,
        default=ReasonChoices.OTHER,
    )
    reference = models.CharField(_("مرجع"), max_length=100, blank=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
        verbose_name=_("سفارش مرتبط"),
    )
    operator = models.CharField(_("اپراتور"), max_length=100)
    notes = models.TextField(_("یادداشت"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("تراکنش انبار")
        verbose_name_plural = _("تراکنش‌های انبار")
        ordering = ["-created_at"]

    def __str__(self):
        arrow = "↓" if self.type == self.TypeChoices.IN else "↑"
        return f"{arrow} {self.product.name} × {self.quantity}"


# ====================================================================
# DAILY PRESENTATION REPORT (گزارش روزانه پرزنت)
# ====================================================================
class DailyReport(models.Model):
    """Daily sales/marketing presentation report."""

    class ActivityType(models.TextChoices):
        VISIT = "visit", _("ویزیت حضوری")
        CALL = "call", _("تماس تلفنی")
        PRESENTATION = "presentation", _("ارائه پرزنت")
        DEMO = "demo", _("دمو محصول")
        FOLLOW_UP = "follow_up", _("پیگیری")
        DELIVERY = "delivery", _("تحویل")

    presenter_name = models.CharField(_("نام پرزنت‌کار"), max_length=150)
    report_date = models.DateField(_("تاریخ گزارش"))
    activity_type = models.CharField(
        _("نوع فعالیت"),
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.VISIT,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_reports",
        verbose_name=_("مشتری"),
    )
    visits_count = models.PositiveIntegerField(_("تعداد ویزیت"), default=0)
    calls_count = models.PositiveIntegerField(_("تعداد تماس"), default=0)
    products_presented = models.PositiveIntegerField(_("محصولات ارائه‌شده"), default=0)
    new_customers = models.PositiveIntegerField(_("مشتریان جدید"), default=0)
    sales_amount = models.PositiveIntegerField(_("مبلغ فروش"), default=0)
    notes = models.TextField(_("یادداشت"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("گزارش روزانه")
        verbose_name_plural = _("گزارش‌های روزانه")
        ordering = ["-report_date"]

    def __str__(self):
        return f"{self.presenter_name} - {self.report_date}"


# ====================================================================
# COMMISSION (پورسانت مشتریان)
# ====================================================================
class Commission(models.Model):
    """Commission record for customers (default 20%)."""

    class StatusChoices(models.TextChoices):
        PENDING = "pending", _("در انتظار")
        APPROVED = "approved", _("تأیید شده")
        PAID = "paid", _("پرداخت شده")
        CANCELLED = "cancelled", _("لغو شده")

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="commissions",
        verbose_name=_("مشتری"),
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="commissions",
        verbose_name=_("سفارش"),
    )
    rate = models.DecimalField(
        _("درصد پورسانت"),
        max_digits=5,
        decimal_places=2,
        default=20.00,
    )
    base_amount = models.PositiveIntegerField(_("مبلغ پایه"), default=0)
    commission_amount = models.PositiveIntegerField(_("مبلغ پورسانت"), default=0)
    status = models.CharField(
        _("وضعیت"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(_("یادداشت"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("پورسانت")
        verbose_name_plural = _("پورسانت‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name} - {self.commission_amount:,}"

    def save(self, *args, **kwargs):
        if not self.commission_amount:
            rate = float(self.rate) / 100
            self.commission_amount = int(self.base_amount * rate)
        super().save(*args, **kwargs)


# ====================================================================
# CHAT MESSAGE (پیام‌ها)
# ====================================================================
class ChatMessage(models.Model):
    """Customer chat message."""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("مشتری"),
    )
    message = models.TextField(_("پیام"))
    from_customer = models.BooleanField(_("از طرف مشتری"), default=True)
    read = models.BooleanField(_("خوانده شده"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("پیام چت")
        verbose_name_plural = _("پیام‌های چت")
        ordering = ["created_at"]

    def __str__(self):
        sender = self.customer.name if self.from_customer else "اپراتور"
        return f"{sender}: {self.message[:50]}"

    @property
    def time_str(self):
        return self.created_at.strftime("%H:%M")


# ====================================================================
# ACTIVITY LOG (Audit Trail)
# ====================================================================
class ActivityLog(models.Model):
    """Log of all user activities in the system."""

    class ActionChoices(models.TextChoices):
        LOGIN = "login", _("ورود به سیستم")
        LOGOUT = "logout", _("خروج از سیستم")
        CREATE = "create", _("ایجاد")
        UPDATE = "update", _("ویرایش")
        DELETE = "delete", _("حذف")
        VIEW = "view", _("مشاهده")
        PAYMENT = "payment", _("ثبت پرداخت")
        ORDER = "order", _("ثبت سفارش")
        REPORT = "report", _("ثبت گزارش")
        SEND = "send", _("ارسال")
        EXPORT = "export", _("خروجی اکسل")

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("کاربر"),
    )
    user_name = models.CharField(_("نام کاربر"), max_length=150)
    action = models.CharField(_("نوع فعالیت"), max_length=20, choices=ActionChoices.choices)
    module = models.CharField(_("بخش"), max_length=100)
    description = models.CharField(_("توضیحات"), max_length=500)
    object_id = models.CharField(_("شناسه شیء"), max_length=100, blank=True)
    object_repr = models.CharField(_("نام شیء"), max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(_("آدرس IP"), null=True, blank=True)
    user_agent = models.TextField(_("User Agent"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("لاگ فعالیت")
        verbose_name_plural = _("لاگ فعالیت‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user_name} - {self.get_action_display()} - {self.created_at:%Y/%m/%d %H:%M}"

    @property
    def time_str(self):
        return self.created_at.strftime("%H:%M")

    @property
    def date_str(self):
        return self.created_at.strftime("%Y/%m/%d")

    @property
    def action_icon(self):
        icons = {
            "login": "🔑", "logout": "🚪", "create": "➕", "update": "✏️",
            "delete": "🗑️", "view": "👁️", "payment": "💳", "order": "🛒",
            "report": "📋", "send": "📤", "export": "📊",
        }
        return icons.get(self.action, "•")

    @property
    def action_color(self):
        colors = {
            "login": "info", "logout": "neutral", "create": "success",
            "update": "warning", "delete": "danger", "view": "neutral",
            "payment": "success", "order": "teal", "report": "info",
            "send": "info", "export": "teal",
        }
        return colors.get(self.action, "neutral")
