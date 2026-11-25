"""
Middleware for automatic activity logging and staff/customer area separation.
"""

from django.shortcuts import redirect

from .activity import log_activity, get_client_ip, get_user_name
from .models import ActivityLog


# Map URL paths to modules and actions for automatic logging
URL_MODULE_MAP = {
    "/products/add/": ("محصولات", "create", "افزودن محصول"),
    "/products/": ("محصولات", "view", "مشاهده لیست محصولات"),
    "/specialists/add/": ("متخصصان زخم", "create", "افزودن متخصص"),
    "/specialists/": ("متخصصان زخم", "view", "مشاهده لیست متخصصان"),
    "/clinics/add/": ("مراکز درمانی", "create", "افزودن مرکز درمانی"),
    "/clinics/": ("مراکز درمانی", "view", "مشاهده لیست مراکز درمانی"),
    "/customers/add/": ("مشتریان", "create", "افزودن مشتری"),
    "/customer-tracking/": ("مشتریان", "view", "مشاهده لیست مشتریان"),
    "/customer-order/": ("سفارشات", "order", "ثبت سفارش مشتری"),
    "/brands/add/": ("برندها", "create", "افزودن برند"),
    "/warehouse/add/": ("انبار", "create", "ثبت تراکنش انبار"),
    "/warehouse/": ("انبار", "view", "مشاهده تراکنش‌های انبار"),
    "/invoices/add/": ("فاکتورها", "create", "صدور فاکتور"),
    "/invoices/": ("فاکتورها", "view", "مشاهده لیست فاکتورها"),
    "/payments/add/": ("پرداخت‌ها", "payment", "ثبت پرداخت"),
    "/payments/": ("پرداخت‌ها", "view", "مشاهده لیست پرداخت‌ها"),
    "/daily-report/": ("گزارشات روزانه", "report", "گزارش روزانه"),
    "/procurement/": ("تدارکات", "send", "درخواست تدارکات"),
    "/chat/": ("چت", "view", "مشاهده چت‌ها"),
    "/inventory/": ("انبار", "view", "مشاهده موجودی انبار"),
    "/income/": ("درآمد", "view", "مشاهده درآمدها"),
    "/request-history/": ("تاریخچه", "view", "مشاهده تاریخچه درخواست‌ها"),
    "/activity-log/": ("لاگ فعالیت", "view", "مشاهده لاگ فعالیت‌ها"),
    "/": ("داشبورد", "view", "مشاهده داشبورد"),
}


class ActivityLogMiddleware:
    """Automatically log user activity based on requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._log(request, response)
        return response

    def _log(self, request, response):
        # Skip if not a successful response or not authenticated
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return
        if response.status_code >= 400:
            return

        # Only log GET (views) and POST (creates)
        if request.method not in ("GET", "POST"):
            return

        # Skip admin, static, media, login, logout
        path = request.path
        if path.startswith("/admin/") or path.startswith("/static/") or path.startswith("/media/"):
            return
        if path in ("/login/", "/logout/"):
            return
        # Skip chat/send AJAX endpoint
        if path == "/chat/send/":
            return

        # Find matching module
        match = None
        for url_prefix, (module, action_get, desc_get) in URL_MODULE_MAP.items():
            if path == url_prefix or path.startswith(url_prefix):
                # For POST, use 'create' or specific action
                if request.method == "POST" and url_prefix.endswith("/add/"):
                    # Already logged explicitly in the view, skip
                    return
                if request.method == "POST" and url_prefix == "/customer-order/":
                    return  # logged explicitly
                if request.method == "POST" and url_prefix == "/daily-report/":
                    return  # logged explicitly
                if request.method == "POST" and url_prefix == "/procurement/":
                    return  # logged explicitly
                if request.method == "POST" and url_prefix == "/income/":
                    return  # logged explicitly
                # For GET, log as view
                if request.method == "GET":
                    match = (module, "view", desc_get)
                break

        if not match:
            return

        module, action, description = match

        # Skip logging GET on dashboard too frequently — only log first hit per session
        # Actually, we'll skip GET on dashboard to reduce noise
        if path == "/" and request.method == "GET":
            return

        # Skip if too many logs in last 5 mins for same user+module+action (avoid duplicates on refresh)
        recent = ActivityLog.objects.filter(
            user=request.user,
            module=module,
            action=action,
            created_at__gte=__import__("django").utils.timezone.now() - __import__("datetime").timedelta(minutes=2),
        ).exists()
        if recent:
            return

        log_activity(
            request,
            action=action,
            module=module,
            description=description,
        )


class PanelAccessMiddleware:
    """Keep staff and customer areas strictly separated.

    - A non-staff authenticated user (a customer) is redirected to /panel/
      if they try to reach any staff URL (anything that is not /panel/, /login/,
      /logout/, /admin/, static or media).
    - A staff user is redirected away from /panel/ to / so they use the staff app.
    """

    PUBLIC_PREFIXES = ("/static/", "/media/", "/admin/")
    PUBLIC_PATHS = ("/login/", "/logout/", "/panel/login/", "/panel/logout/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path

        if user is not None and user.is_authenticated:
            is_panel = path.startswith("/panel/")
            is_public = (
                path in self.PUBLIC_PATHS
                or any(path.startswith(p) for p in self.PUBLIC_PREFIXES)
            )

            if is_panel and not is_public:
                # Staff should not browse the customer panel
                if user.is_staff:
                    return redirect("/")
            else:
                # Non-staff (customer) must stay within the panel
                if not user.is_staff and not is_public:
                    return redirect("/panel/")

        return self.get_response(request)
