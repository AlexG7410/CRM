"""
Custom template tags and filters for the CRM app.
"""

from django import template
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.filter
def persian_digits(value):
    """Convert Latin digits to Persian digits."""
    if value is None:
        return ""
    persian = "۰۱۲۳۴۵۶۷۸۹"
    return str(value).translate(str.maketrans("0123456789", persian))


@register.filter
def fa_currency(value):
    """Format value as Persian currency (Toman)."""
    if value is None or value == "":
        return "۰"
    try:
        num = int(float(value))
        s = f"{num:,}"
        persian = "۰۱۲۳۴۵۶۷۸۹"
        s = s.translate(str.maketrans("0123456789", persian))
        return f"{s} تومان"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def fa_number(value):
    """Format number with thousand separators in Persian."""
    if value is None or value == "":
        return "۰"
    try:
        num = int(float(value))
        s = f"{num:,}"
        persian = "۰۱۲۳۴۵۶۷۸۹"
        return s.translate(str.maketrans("0123456789", persian))
    except (ValueError, TypeError):
        return str(value)


@register.simple_tag
def status_badge_class(status_value, mapping=None):
    """Return Bootstrap-like CSS class for status."""
    default_mapping = {
        # Order status
        "pending": "neutral",
        "processing": "warning",
        "shipped": "info",
        "delivered": "success",
        "cancelled": "danger",
        # Payment status
        "paid": "success",
        "unpaid": "danger",
        "partial": "warning",
        # Invoice status
        "draft": "neutral",
        "sent": "info",
        "overdue": "danger",
        # Specialist status
        "available": "success",
        "busy": "warning",
        "off": "neutral",
        # Payment record status
        "confirmed": "success",
        "failed": "danger",
        # Procurement status
        "approved": "info",
        "rejected": "danger",
        "fulfilled": "success",
        # Customer status
        "active": "success",
        "inactive": "neutral",
    }
    if mapping and status_value in mapping:
        return mapping[status_value]
    return default_mapping.get(status_value, "neutral")


@register.simple_tag
def status_label(status_value):
    """Return Persian label for status code."""
    labels = {
        "pending": "در انتظار",
        "processing": "در حال پردازش",
        "shipped": "ارسال شده",
        "delivered": "تحویل شده",
        "cancelled": "لغو شده",
        "paid": "پرداخت شده",
        "unpaid": "پرداخت نشده",
        "partial": "پرداخت جزئی",
        "draft": "پیش‌نویس",
        "sent": "ارسال شده",
        "overdue": "سررسید گذشته",
        "available": "آزاد",
        "busy": "مشغول",
        "off": "غیرفعال",
        "confirmed": "تأیید شد",
        "failed": "ناموفق",
        "approved": "تأیید شد",
        "rejected": "رد شد",
        "fulfilled": "تأمین شد",
        "active": "فعال",
        "inactive": "غیرفعال",
    }
    return labels.get(status_value, status_value)


@register.simple_tag
def priority_color(priority):
    """Return color for procurement priority."""
    colors = {
        "urgent": "#dc2626",
        "high": "#f59e0b",
        "medium": "#06b6d4",
        "low": "#10b981",
    }
    return colors.get(priority, "#64748b")


@register.simple_tag
def priority_label(priority):
    """Return Persian label for priority."""
    labels = {
        "urgent": "اضطراری",
        "high": "زیاد",
        "medium": "متوسط",
        "low": "کم",
    }
    return labels.get(priority, priority)


@register.simple_tag
def payment_method_label(method):
    """Return Persian label for payment method."""
    labels = {
        "card": "کارت بانکی",
        "transfer": "انتقال بانکی",
        "cash": "نقدی",
        "cheque": "چک",
    }
    return labels.get(method, method)


@register.simple_tag
def avatar_gradient(color):
    """Return gradient class for avatar based on color."""
    gradients = {
        "teal": "from-teal-500 to-teal-700",
        "emerald": "from-emerald-500 to-emerald-700",
        "cyan": "from-cyan-500 to-teal-600",
    }
    return gradients.get(color, gradients["teal"])


@register.simple_tag
def percentage(part, total):
    """Calculate percentage."""
    if not total:
        return 0
    return round((part / total) * 100, 1)


@register.filter
def filter_by_type(customers, type_value):
    """Filter customers by type."""
    return [c for c in customers if c.type == type_value]
