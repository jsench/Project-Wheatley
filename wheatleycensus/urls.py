# marlowecensus/urls.py

from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from django.contrib import admin
from . import views

urlpatterns = [
    # Home & search
    path('', views.homepage, name='homepage'),
    path('homepage', views.homepage, name='homepage'),
    path('search/', views.search, name='search'),
    path('search/<str:field>/<str:value>/', views.search, name='search'),
    path('search/<str:field>/<str:value>/<str:order>/', views.search, name='search'),

    # Title → issue list
    path('title/<int:id>/', views.issue_list, name='issue_list'),

    # Issue → copy list
    path('issue/<int:id>/', views.copy_list, name='copy_list'),

    # AJAX/modal copy details
    path('copydata/<int:copy_id>/', views.copy_data, name='copy_data'),

    # Static copy URL
    path('wc/<int:wc_number>/', views.static_copy, name='copy_page'),

    # About / static pages
    path('about/', views.about, name='about'),
    path('about/<str:viewname>/', views.about, name='about'),

    # Autocomplete
    path('autofill/location/', views.autofill_location, name='autofill_location'),
    path('autofill/location/<str:query>/', views.autofill_location, name='autofill_location'),
    path('autofill/provenance/', views.autofill_provenance, name='autofill_provenance'),
    path('autofill/provenance/<str:query>/', views.autofill_provenance, name='autofill_provenance'),
    path('autofill/collection/', views.autofill_collection, name='autofill_collection'),
    path('autofill/collection/<str:query>/', views.autofill_collection, name='autofill_collection'),

    # CSV exports
    path('location_copy_count_csv_export/', views.location_copy_count_csv_export, name='location_copy_count_csv_export'),
    path('year_issue_copy_count_csv_export/', views.year_issue_copy_count_csv_export, name='year_issue_copy_count_csv_export'),
    path('export/<str:groupby>/<str:column>/<str:aggregate>/', views.export, name='export'),

    # Auth
    path('login', views.login_user, name='login_user'),
    path('logout', views.logout_user, name='logout_user'),

    # Admin
    path(settings.ADMIN_URL, admin.site.urls),
]

# <<< CHANGED HERE >>>
# Instead of trying to put + static() on the next line (which Python parses
# as a unary plus), do one of:

# 1) Use +=
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# —or—

# 2) Keep the + on the same line as your list:
# urlpatterns = [
#     ... your patterns ...
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
#   + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
