"""
Django admin for the Wound Specialist CRM.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Customer,
    Brand,
    Product,
    Consultation,
    SatisfactionReview,
    Order,
    OrderItem,
    Invoice,
    Payment,
    ProductRequest,
    WarehouseMovement,
    DailyReport,
    Commission,
    ChatMessage,
    ActivityLog,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("logo_emoji", "name", "country", "product_count_display")
    list_display_links = ("name",)
    search_fields = ("name", "country")

    @admin.display(description=_("تعداد محصولات"))
    def product_count_display(self, obj):
        return obj.product_count


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("image_emoji", "name", "brand", "category", "wound_type", "price", "stock", "is_active")
    list_display_links = ("name",)
    list_filter = ("brand", "category", "wound_type", "is_active")
    search_fields = ("name", "description", "brand__name")
    list_editable = ("price", "is_active")
    list_per_page = 25


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "contact_person", "phone", "city", "commission_rate", "status")
    list_display_links = ("name",)
    list_filter = ("type", "status", "city")
    search_fields = ("name", "phone", "contact_person", "city")
    list_editable = ("status",)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "phone", "wound_type", "status", "created_at")
    list_display_links = ("customer_name",)
    list_filter = ("status", "wound_type")
    search_fields = ("customer_name", "phone", "question")


@admin.register(SatisfactionReview)
class SatisfactionReviewAdmin(admin.ModelAdmin):
    list_display = ("customer", "rating", "product_quality", "service_quality", "delivery_speed", "created_at")
    list_display_links = ("customer",)
    list_filter = ("rating",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ("product", "quantity", "unit_price", "subtotal_display")
    readonly_fields = ("subtotal_display",)

    @admin.display(description=_("جمع"))
    def subtotal_display(self, obj):
        if obj.id:
            return f"{obj.subtotal:,}"
        return "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "total_items", "total_display", "commission_amount", "status", "created_at")
    list_display_links = ("number",)
    list_filter = ("status", "payment_status", "created_at")
    search_fields = ("number", "customer__name")
    inlines = [OrderItemInline]

    @admin.display(description=_("مبلغ کل"))
    def total_display(self, obj):
        if obj.id:
            return f"{obj.total:,}"
        return "—"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "type", "total", "status", "issue_date")
    list_display_links = ("number",)
    list_filter = ("type", "status", "issue_date")
    search_fields = ("number", "customer__name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("customer", "invoice", "amount", "method", "status", "created_at")
    list_display_links = ("customer",)
    list_filter = ("method", "status")
    search_fields = ("customer__name", "invoice__number")


@admin.register(ProductRequest)
class ProductRequestAdmin(admin.ModelAdmin):
    list_display = ("customer", "product_name", "quantity", "status", "created_at")
    list_display_links = ("customer",)
    list_filter = ("status",)
    search_fields = ("customer__name", "product_name")


@admin.register(WarehouseMovement)
class WarehouseMovementAdmin(admin.ModelAdmin):
    list_display = ("type_colored", "product", "quantity", "reason", "operator", "created_at")
    list_display_links = ("product",)
    list_filter = ("type", "reason", "created_at")
    search_fields = ("product__name", "operator")

    @admin.display(description=_("نوع"))
    def type_colored(self, obj):
        if obj.type == "in":
            return format_html('<span style="color:#10b981; font-weight:700;">↓ ورودی</span>')
        return format_html('<span style="color:#dc2626; font-weight:700;">↑ خروجی</span>')


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ("presenter_name", "report_date", "activity_type", "visits_count", "calls_count", "sales_amount")
    list_display_links = ("presenter_name",)
    list_filter = ("activity_type", "report_date")
    search_fields = ("presenter_name",)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ("customer", "order", "rate", "commission_amount", "status", "created_at")
    list_display_links = ("customer",)
    list_filter = ("status",)
    search_fields = ("customer__name",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action_icon_display", "user_name", "action_colored", "module", "description", "ip_address", "created_at")
    list_display_links = ("description",)
    list_filter = ("action", "module", "created_at", "user")
    search_fields = ("user_name", "description", "module", "ip_address")
    readonly_fields = ("user", "user_name", "action", "module", "description", "object_id", "object_repr", "ip_address", "user_agent", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description=_("فعالیت"), ordering="action")
    def action_icon_display(self, obj):
        return f"{obj.action_icon} {obj.get_action_display()}"

    @admin.display(description=_("نوع"), ordering="action")
    def action_colored(self, obj):
        colors = {"login": "#06b6d4", "logout": "#64748b", "create": "#10b981",
                  "update": "#f59e0b", "delete": "#e11d48", "view": "#64748b",
                  "payment": "#10b981", "order": "#0d9488", "report": "#06b6d4",
                  "send": "#06b6d4", "export": "#0d9488"}
        color = colors.get(obj.action, "#64748b")
        return format_html('<span style="color:{}; font-weight:700;">● {}</span>', color, obj.get_action_display())
