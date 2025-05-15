# wheatleycensus/urls.py
# This file defines all the URL routes for the Wheatley Census app.
# URL patterns are grouped by main site, CSV exports, autocomplete, and authentication.
#
# Changes to this file affect which URLs are available in your web app and which views handle them.
# Adding, removing, or renaming a path here will change how users and the app access different features.

from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from django.contrib import admin
from . import views

urlpatterns = [
    # --- Main Site URLs ---
    # These URLs handle the main navigation and core features of the site.
    # Changing these will affect how users access the homepage, search, and detail pages.
    path('',                        views.homepage,        name='homepage'),
    path('search/',                 views.search,          name='search'),
    path('title/<int:id>/',         views.issue_list,      name='issue_list'),
    path('issue/<int:id>/',         views.copy_list,       name='copy_list'),
    path('copydata/<int:copy_id>/', views.copy_data,       name='copy_data'),
    path('copy/<int:census_id>/',   views.cen_copy_modal,  name='cen_copy_modal'),
    path('wc/<int:wc_number>/',     views.copy_page,       name='copy_page'),
    path('about/',                  views.about,           name='about'),
    path('about/advisoryboard/',    views.about,           name='advisoryboard'),
    path('about/references/',       views.about,           name='references'),
    path('about/contact/',          views.about,           name='contact'),

    # --- Autocomplete URLs ---
    # These endpoints provide AJAX autocomplete for forms and search fields.
    # Changing these will affect dynamic suggestions in the UI.
    path('autofill/location/',                views.autofill_location,   name='autofill_location'),
    path('autofill/location/<str:query>/',    views.autofill_location,   name='autofill_location'),
    path('autofill/provenance/',              views.autofill_provenance, name='autofill_provenance'),
    path('autofill/provenance/<str:query>/',  views.autofill_provenance, name='autofill_provenance'),
    path('autofill/collection/',              views.autofill_collection, name='autofill_collection'),
    path('autofill/collection/<str:query>/',  views.autofill_collection, name='autofill_collection'),

    # --- CSV Export URLs ---
    # These endpoints allow users to download data as CSV files.
    # Changing these will affect data export features.
    path('location_copy_count_csv_export/',   views.location_copy_count_csv_export,  name='location_copy_count_csv_export'),
    path('year_issue_copy_count_csv_export/', views.year_issue_copy_count_csv_export, name='year_issue_copy_count_csv_export'),
    path('export/<str:groupby>/<str:column>/<str:aggregate>/', views.export, name='export'),

    # --- Authentication URLs ---
    # These URLs handle user login, logout, and admin access.
    # Changing these will affect how users and admins sign in/out and access the admin panel.
    path('login',                   views.login_user,      name='login_user'),
    path('logout',                  views.logout_user,     name='logout_user'),
    path(settings.ADMIN_URL,        admin.site.urls),
]

# --- Static & Media File Serving (Development Only) ---
# These lines allow Django to serve static and media files during development.
# In production, use a proper web server for static/media files.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
