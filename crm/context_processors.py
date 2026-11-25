"""
Context processors for the CRM app.
"""

from django.conf import settings


def global_context(request):
    """Add global context variables to all templates."""
    nav_groups = [
        {
            "title": "اصلی",
            "items": [
                {"id": "dashboard", "label": "داشبورد", "icon": "dashboard"},
            ],
        },
        {
            "title": "مشتریان",
            "items": [
                {"id": "customers", "label": "مشتریان", "icon": "users"},
                {"id": "consultation", "label": "مشاوره آنلاین", "icon": "chat"},
                {"id": "satisfaction", "label": "رضایت مندی", "icon": "star"},
                {"id": "commissions", "label": "پورسانت مشتریان", "icon": "percent"},
            ],
        },
        {
            "title": "محصولات و انبار",
            "items": [
                {"id": "products", "label": "محصولات", "icon": "package"},
                {"id": "inventory", "label": "موجودی انبار + قیمت", "icon": "warehouse"},
                {"id": "warehouse", "label": "انبار و خروجی", "icon": "boxes"},
                {"id": "warehouse_add", "label": "ثبت ورود/خروج", "icon": "send"},
            ],
        },
        {
            "title": "فروش و تدارکات",
            "items": [
                {"id": "product_request", "label": "فرم درخواست محصول", "icon": "clipboard"},
                {"id": "procurement", "label": "تدارکات", "icon": "send"},
                {"id": "customer_order", "label": "ثبت سفارش", "icon": "cart"},
                {"id": "orders_list", "label": "لیست سفارش‌ها", "icon": "list"},
            ],
        },
        {
            "title": "مالی",
            "items": [
                {"id": "invoices", "label": "فاکتور", "icon": "file"},
                {"id": "payments", "label": "پرداخت", "icon": "credit"},
                {"id": "financial_tracking", "label": "پیگیری مالی", "icon": "trending"},
            ],
        },
        {
            "title": "گزارشات",
            "items": [
                {"id": "sales_report", "label": "گزارش فروش بازاریابی", "icon": "chart"},
                {"id": "daily_report", "label": "گزارش روزانه پرزنت", "icon": "clipboard"},
            ],
        },
        {
            "title": "سیستم",
            "items": [
                {"id": "activity_log", "label": "لاگ فعالیت‌ها", "icon": "history"},
            ],
        },
    ]
    return {
        "nav_groups": nav_groups,
        "app_name": "APP CRM متخصص",
        "app_description": "سامانه مدیریت متخصص کلینیک زخم",
    }
