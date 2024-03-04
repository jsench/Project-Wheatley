from django.contrib import admin, auth
from import_export.admin import ImportExportModelAdmin
from . import models


### Administrative Tables
admin.site.unregister(auth.models.Group)

admin.site.unregister(auth.get_user_model())
@admin.register(auth.get_user_model())
class UserDetailAdmin(ImportExportModelAdmin):
    list_display = ['username']

@admin.register(models.Location)
class LocationAdmin(ImportExportModelAdmin):
    ordering = ('name',)

@admin.register(models.StaticPageText)
class StaticPageTextAdmin(ImportExportModelAdmin):
    pass


### Core Data Tables

# Provenance tables

class ProvenanceOwnershipInline(admin.TabularInline):
    model = models.ProvenanceOwnership
    search_fields = ('owner',)
    autocomplete_fields = ('owner',)
    extra = 1

@admin.register(models.ProvenanceName)
class ProvenanceNameAdmin(ImportExportModelAdmin):
    ordering = ('name',)
    search_fields = ('name',)
    inlines = (ProvenanceOwnershipInline,)

@admin.register(models.ProvenanceOwnership)
class ProvenanceOwnershipAdmin(ImportExportModelAdmin):
    search_fields = ('owner',)
    autocomplete_fields = ('owner',)

# Higher-level FRBR categories

@admin.register(models.Title)
class TitleAdmin(ImportExportModelAdmin):
    ordering = ('title',)

@admin.register(models.Issue)
class IssueAdmin(ImportExportModelAdmin):
    pass

@admin.register(models.Edition)
class EditionAdmin(ImportExportModelAdmin):
    pass

# Copy table

@admin.register(models.Copy)
class CopyAdmin(ImportExportModelAdmin):
    list_filter=['verification']
    #inlines = (ProvenanceOwnershipInline,)
    #search_fields = ('MC', 'issue__edition__title__title')
