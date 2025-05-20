# wheatleycensus/admin.py
# Registers models with the Django admin interface and customizes their display.
# Organized by model category for clarity and maintainability.

from django.contrib import admin
from . import models

# =====================
# Inline Admin Classes
# =====================

# ProvenanceRecord inline for use in ProvenanceName and Copy admin
class ProvenanceRecordInline(admin.TabularInline):
    model = models.ProvenanceRecord
    extra = 1
    fields = ('provenance_name',)

# Copy inline for use in Issue and Edition admin
class CopyInline(admin.TabularInline):
    model = models.Copy
    extra = 1
    fields = ('wc_number','issue','location','shelfmark','verification','signed_by_author')
    ordering = ('wc_number',)

# Issue inline for use in Edition admin
class IssueInline(admin.TabularInline):
    model = models.Issue
    extra = 1
    fields = ('year','start_date','end_date','notes','bibliographic_data')  # include new field
    inlines = [CopyInline]
    ordering = ('year',)

# Edition inline for use in Title admin
class EditionInline(admin.TabularInline):
    model = models.Edition
    extra = 1
    fields = ('edition_number','edition_format','notes')
    inlines = [IssueInline]
    ordering = ('edition_number',)

# =====================
# Location Admin
# =====================
@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name_of_library_collection','us_state_or_non_us_nation','latitude','longitude')
    search_fields = ('name_of_library_collection',)
    list_filter = ('us_state_or_non_us_nation',)

# =====================
# Provenance Admin
# =====================
@admin.register(models.ProvenanceName)
class ProvenanceNameAdmin(admin.ModelAdmin):
    list_display  = ('name','start_century','end_century','gender','viaf')
    search_fields = ('name',)
    list_filter   = ('start_century','end_century','gender')
    inlines       = (ProvenanceRecordInline,)

@admin.register(models.ProvenanceRecord)
class ProvenanceRecordAdmin(admin.ModelAdmin):
    list_display  = ('provenance_name','copy')
    search_fields = ('provenance_name__name','copy__wc_number')
    list_filter   = ('provenance_name',)

# =====================
# Bibliographic Admin (Title, Edition, Issue, Copy)
# =====================
@admin.register(models.Title)
class TitleAdmin(admin.ModelAdmin):
    list_display  = ('title','edition_count','copy_count')
    search_fields = ('title',)
    inlines       = (EditionInline,)

    def edition_count(self,obj):
        """Return the number of editions for this title."""
        return obj.edition_set.count()
    edition_count.short_description = "Editions"

    def copy_count(self,obj):
        """Return the number of copies for this title."""
        return models.Copy.objects.filter(issue__edition__title=obj).count()
    copy_count.short_description = "Copies"

@admin.register(models.Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display  = ('title','edition_number','edition_format')
    search_fields = ('title__title',)
    list_filter   = ('edition_format',)
    inlines       = (IssueInline,)

@admin.register(models.Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display  = ('edition','year','start_date','end_date','bibliographic_data')  # new
    search_fields = ('edition__title__title','year')
    list_filter   = ('year',)
    inlines       = (CopyInline,)

@admin.register(models.Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display  = ('wc_number','issue','location','shelfmark','verification','signed_by_author')
    search_fields = ('wc_number','issue__edition__title__title','location__name_of_library_collection')
    list_filter   = ('verification','fragment','from_estc')
    inlines       = (ProvenanceRecordInline,)
    list_per_page = 25

# =====================
# Static Page Text Admin
# =====================
@admin.register(models.StaticPageText)
class StaticPageTextAdmin(admin.ModelAdmin):
    list_display  = ('viewname','content')
    search_fields = ('viewname','content')
