"""URL configuration for woundcare_crm project."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("crm.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "سامانه مدیریت ارتباط با مشتریان زخم‌شفـا"
admin.site.site_title = "زخم‌شفـا CRM"
admin.site.index_title = "پنل مدیریت"
admin.site.enable_nav_sidebar = True
