from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('rides/', include('rides.urls')),
    path('tickets/', include('tickets.urls')),
    path('payments/', include('payments.urls')),
    path('admin-dashboard/', include('admin_dashboard.urls')),
    path('', lambda r: redirect('/rides/landing/')),
]

# 👇 Add this block at the very bottom
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # optional