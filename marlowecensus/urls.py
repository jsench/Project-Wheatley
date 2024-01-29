from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from django.contrib import admin
from . import views

urlpatterns = [
    # Main site functionality
    path('', views.homepage, name='homepage'),
    path('', views.homepage, name='home'),
    path('homepage', views.homepage, name='homepage'),
    path('search/', views.search, name='search'),
    path('search/<str:field>/<str:value>/', views.search, name='search'),
    path('search/<str:field>/<str:value>/<str:order>/', views.search, name='search'),
    path('editions/<int:id>/', views.detail, name='detail'),
    path('about/', views.about, name='about'),
    path('about/<str:viewname>/', views.about, name='about'),
    path('copy/<int:id>/', views.copy, name='copy'),
    path('copydata/<int:copy_id>/', views.copy_data, name='copy_data'),
    path('cen/<int:cen>/', views.cen_copy_modal, name='cen_copy_modal'),

    # Search autocomplete
    path('autofill/location/', views.autofill_location, name='autofill_location'),
    path('autofill/location/<str:query>/', views.autofill_location, name='autofill_location'),
    path('autofill/provenance/', views.autofill_provenance, name='autofill_provenance'),
    path('autofill/provenance/<str:query>/', views.autofill_provenance, name='autofill_provenance'),
    path('autofill/collection/', views.autofill_collection, name='autofill_collection'),
    path('autofill/collection/<str:query>/', views.autofill_collection, name='autofill_collection'),

    # Data export
    path('location_copy_count_csv_export/',
        views.location_copy_count_csv_export,
        name='location_copy_count_csv_export'),
    path('year_issue_copy_count_csv_export/',
        views.year_issue_copy_count_csv_export,
        name='year_issue_copy_count_csv_export'),
    path('export/<str:groupby>/<str:column>/<str:aggregate>/',
        views.export, name='export'),

    # User accounts and management
    path('login', views.login_user, name='login_user'),
    path('logout', views.logout_user, name='logout_user'),

    # Admin panel
    path(settings.ADMIN_URL, admin.site.urls, name='admin'),

] + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
