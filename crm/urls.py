"""URL configuration for the CRM app."""

from django.urls import path
from . import views
from . import panel_views

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Main
    path("", views.dashboard, name="dashboard"),

    # 1. Customers (مشتریان)
    path("customers/", views.customers, name="customers"),
    path("customers/add/", views.customer_add, name="customer_add"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/export/excel/", views.customers_export_excel, name="customers_export_excel"),

    # 2. Products (محصولات)
    path("products/", views.products, name="products"),
    path("products/add/", views.product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("brands/add/", views.brand_add, name="brand_add"),

    # 3. Online Consultation (مشاوره آنلاین)
    path("consultation/", views.consultation, name="consultation"),
    path("consultation/add/", views.consultation_add, name="consultation_add"),
    path("consultation/<int:pk>/answer/", views.consultation_answer, name="consultation_answer"),

    # 4. Satisfaction (رضایت مندی)
    path("satisfaction/", views.satisfaction, name="satisfaction"),
    path("satisfaction/add/", views.satisfaction_add, name="satisfaction_add"),

    # 5. Inventory (لیست موجودی انبار + قیمت)
    path("inventory/", views.inventory, name="inventory"),

    # 6. Invoices (فاکتور)
    path("invoices/", views.invoices, name="invoices"),
    path("invoices/add/", views.invoice_add, name="invoice_add"),
    path("invoices/<int:pk>/approve/", views.invoice_approve, name="invoice_approve"),
    path("invoices/<int:pk>/issue/", views.invoice_issue, name="invoice_issue"),

    # 7. Payments (پرداخت)
    path("payments/", views.payments, name="payments"),
    path("payments/add/", views.payment_add, name="payment_add"),

    # 8. Commissions (پورسانت مشتریان)
    path("commissions/", views.commissions, name="commissions"),
    path("commissions/<int:pk>/approve/", views.commission_approve, name="commission_approve"),
    path("commissions/<int:pk>/pay/", views.commission_pay, name="commission_pay"),

    # 9. Sales Report (گزارش فروش بازاریابی)
    path("sales-report/", views.sales_report, name="sales_report"),
    path("sales-report/export/excel/", views.sales_report_export_excel, name="sales_report_export_excel"),

    # 10. Product Request (فرم درخواست محصول)
    path("product-request/", views.product_request, name="product_request"),
    path("product-request/add/", views.product_request_add, name="product_request_add"),

    # 11. Procurement (تدارکات)
    path("procurement/", views.procurement, name="procurement"),
    path("procurement/<int:pk>/complete/", views.procurement_complete, name="procurement_complete"),

    # 11b. Workflow: Send to Finance/Warehouse/Procurement
    path("product-request/<int:pk>/send-to-finance/", views.product_request_send_to_finance, name="product_request_send_to_finance"),
    path("product-request/<int:pk>/send-to-warehouse/", views.product_request_send_to_warehouse, name="product_request_send_to_warehouse"),
    path("product-request/<int:pk>/send-to-procurement/", views.product_request_send_to_procurement, name="product_request_send_to_procurement"),
    path("product-request/<int:pk>/mark-in-progress/", views.product_request_mark_in_progress, name="product_request_mark_in_progress"),

    # 12-14. Order workflow
    path("customer-order/", views.customer_order, name="customer_order"),
    path("orders/", views.orders_list, name="orders_list"),
    path("orders/<int:pk>/ship/", views.order_ship, name="order_ship"),
    path("orders/<int:pk>/deliver/", views.order_deliver, name="order_deliver"),
    path("orders/<int:pk>/confirm-receipt/", views.order_confirm_receipt, name="order_confirm_receipt"),

    # Warehouse
    path("warehouse/", views.warehouse, name="warehouse"),
    path("warehouse/add/", views.warehouse_add, name="warehouse_add"),

    # 15. Financial Tracking (پیگیری مالی)
    path("financial-tracking/", views.financial_tracking, name="financial_tracking"),

    # 16. Daily Report (گزارش روزانه پرزنت)
    path("daily-report/", views.daily_report, name="daily_report"),

    # Activity Log
    path("activity-log/", views.activity_log, name="activity_log"),

    # ====================================================================
    # CUSTOMER PANEL (پنل مشتری) — separate self-service panel
    # ====================================================================
    path("panel/login/", panel_views.panel_login, name="panel_login"),
    path("panel/logout/", panel_views.panel_logout, name="panel_logout"),
    path("panel/", panel_views.panel_dashboard, name="panel_dashboard"),
    path("panel/orders/", panel_views.panel_orders, name="panel_orders"),
    path("panel/orders/new/", panel_views.panel_order_new, name="panel_order_new"),
    path("panel/orders/<int:pk>/", panel_views.panel_order_detail, name="panel_order_detail"),
    path("panel/commissions/", panel_views.panel_commissions, name="panel_commissions"),
    path("panel/invoices/", panel_views.panel_invoices, name="panel_invoices"),
    path("panel/consultation/", panel_views.panel_consultation, name="panel_consultation"),
    path("panel/review/", panel_views.panel_review_add, name="panel_review_add"),
    path("panel/profile/", panel_views.panel_profile, name="panel_profile"),
]
