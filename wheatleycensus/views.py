# wheatleycensus/views.py
# This file contains all the view functions for the Wheatley Census Django app.
# Each section is grouped by functionality: helpers, homepage/search, copy listings, static pages, CSV exports, autocomplete endpoints, and authentication.

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from .constants import US_STATES, WORLD_COUNTRIES
from .models import Copy, Issue, Title, Location, ProvenanceName, StaticPageText  # CanonicalCopy removed
from datetime import datetime
import csv
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.db.models import ObjectDoesNotExist

# ------------------------------------------------------------------------------
# Query Constants
# ------------------------------------------------------------------------------
canonical_query = Q(verification='U') | Q(verification='V')
unverified_query = Q(verification='U')
verified_query = Q(verification='V')
false_query = Q(verification='F')

# ------------------------------------------------------------------------------
# Utility function for icon path
# ------------------------------------------------------------------------------
def get_icon_path(title):
    if title.image:
        return title.image.url
    return 'census/images/generic-title-icon.png'


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
# Utility functions for string manipulation, sorting, and year range parsing.
def strip_article(s):
    """Remove leading articles from a string."""
    articles = ['a ', 'A ', 'an ', 'An ', 'the ', 'The ']
    for a in articles:
        if s.startswith(a):
            return s.replace(a, '', 1)
    return s


def convert_year_range(year):
    """Convert a year range string to start and end years."""
    if '-' in year:
        start, end = [n.strip() for n in year.split('-', 1)]
        if len(start) == 4 and start.isdigit() and len(end) == 4 and end.isdigit():
            return int(start), int(end)
    elif len(year) == 4 and year.isdigit():
        return int(year), int(year)
    return False


def title_sort_key(title_object):
    """Sort key for titles, handling numeric prefixes."""
    title = title_object.title
    if title and title[0].isdigit():
        title = title.split()
        return strip_article(' '.join(title[1:] + [title[0]]))
    return strip_article(title)


def copy_sort_key(c):
    """Sort key for copies based on location and shelfmark."""
    census_id_a, census_id_b = copy_census_id_sort_key(c)
    return (copy_location_sort_key(c),
            copy_shelfmark_sort_key(c),
            census_id_a,
            census_id_b)


def copy_census_id_sort_key(c):
    """Sort key for census IDs, handling numeric and alphanumeric formats."""
    wc_number = c.wc_number if hasattr(c, 'wc_number') and c.wc_number is not None else ''
    wc_number_a = 0
    wc_number_b = 0
    try:
        if '.' in wc_number:
            wc_number_a, wc_number_b = wc_number.split('.')
            wc_number_a, wc_number_b = int(wc_number_a), int(wc_number_b)
        else:
            wc_number_a = int(wc_number)
    except ValueError:
        pass
    return (wc_number_a, wc_number_b)


def copy_location_sort_key(c):
    """Sort key for copy locations."""
    if c.location is not None:
        name = getattr(c.location, 'name_of_library_collection', '')
    else:
        name = ''
    return strip_article(name if name else '')


def copy_shelfmark_sort_key(c):
    """Sort key for copy shelfmarks."""
    sm = c.shelfmark
    return sm if sm else ''


# ------------------------------------------------------------------------------
# Homepage & Search
# ------------------------------------------------------------------------------
# homepage: Renders the front page with a grid of titles.
def homepage(request):
    """Display the homepage with a grid of titles."""
    gridwidth = 5
    titlelist = list(Title.objects.all())
    # Sort by earliest issue year (descending), then alphabetically
    def sort_key(title):
        years = []
        for ed in title.edition_set.all():
            for issue in ed.issue_set.all():
                try:
                    y = int(issue.year)
                    years.append(y)
                except Exception:
                    continue
        min_year = min(years) if years else 9999
        return (-min_year, title.title.lower())
    titlelist = sorted(titlelist, key=sort_key)
    titlerows = [titlelist[i: i + gridwidth]
                 for i in range(0, len(titlelist), gridwidth)]
    return render(request, 'census/frontpage.html', {
        'frontpage': True,
        'titlelist': titlelist,
        'titlerows': titlerows,
        'icon_path': 'census/images/generic-title-icon.png'
    })


# search: Unified search endpoint for filtering copies by location, keyword, provenance, gender, or census ID.
def search(request, field=None, value=None, order=None):
    """Search for copies based on various criteria."""
    field = field or request.GET.get('field')
    value = value or request.GET.get('value')
    order = order or request.GET.get('order')
    
    # Base queryset with select_related to optimize database queries
    copy_list = Copy.objects.select_related(
        'location', 
        'issue__edition__title'
    ).filter(canonical_query)
    
    display_field = field
    display_value = value
    
    # Handle different search types
    if field == 'keyword' or field is None and value:
        field = 'keyword'
        display_field = 'Keyword Search'
        query = (Q(marginalia__icontains=value) |
                 Q(binding__icontains=value) |
                 Q(local_notes__icontains=value) |
                 Q(prov_info__icontains=value) |
                 Q(bibliography__icontains=value) |
                 Q(provenance_search_names__name__icontains=value))
        result_list = copy_list.filter(query)
    elif field == 'stc' and value:
        display_field = 'STC / Wing'
        result_list = copy_list.filter(issue__stc_wing__icontains=value)
    elif field == 'census_id' and value:
        display_field = 'MC'
        result_list = copy_list.filter(census_id=value)
    elif field == 'year' and value:
        display_field = 'Year'
        year_range = convert_year_range(value)
        if year_range:
            start, end = year_range
            result_list = copy_list.filter(issue__start_date__lte=end, issue__end_date__gte=start)
        else:
            result_list = copy_list.filter(issue__year__icontains=value)
    elif field == 'location' and value:
        display_field = 'Location'
        result_list = copy_list.filter(location__name__icontains=value)
    elif field == 'provenance_name' and value:
        display_field = 'Provenance Name'
        result_list = copy_list.filter(provenance_search_names__name__icontains=value)
    elif field == 'unverified':
        display_field = 'Unverified'
        display_value = 'All'
        result_list = copy_list.filter(unverified_query)
        if order is None:
            order = 'location'
    elif field == 'ghosts':
        display_field = 'Ghosts'
        display_value = 'All'
        result_list = Copy.objects.filter(false_query)
    elif field == 'collection':
        result_list, display_field = get_collection(copy_list, value)
        display_value = 'All'
    else:
        result_list = Copy.objects.none()

    # Remove duplicates
    result_list = result_list.distinct()
    
    # Apply sorting
    if order == 'date':
        result_list = sorted(result_list, key=lambda c: (
            int(c.issue.start_date),
            title_sort_key(c.issue.edition.title),
            copy_location_sort_key(c)
        ))
    elif order == 'title':
        result_list = sorted(result_list, key=lambda c: (
            title_sort_key(c.issue.edition.title),
            int(c.issue.start_date),
            copy_location_sort_key(c)
        ))
    elif order == 'location':
        result_list = sorted(result_list, key=lambda c: (
            copy_location_sort_key(c),
            int(c.issue.start_date),
            title_sort_key(c.issue.edition.title)
        ))
    elif order == 'stc':
        result_list = sorted(result_list, key=lambda c: (
            c.issue.stc_wing,
            copy_location_sort_key(c)
        ))
    else:  # Default to date sorting
        result_list = sorted(result_list, key=lambda c: (
            int(c.issue.start_date),
            title_sort_key(c.issue.edition.title),
            copy_location_sort_key(c)
        ))

    # Pagination
    paginator = Paginator(result_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'census/search-results.html', {
        'icon_path': 'census/images/generic-title-icon.png',
        'value': value,
        'field': field,
        'display_value': display_value,
        'display_field': display_field,
        'page_obj': page_obj,
        'copy_count': len(result_list)
    })


# ------------------------------------------------------------------------------
# Copy listings & detail modals
# ------------------------------------------------------------------------------
# copy_list: Shows all copies for a given Issue.
def copy_list(request, id):
    """Display all copies for a given issue."""
    selected_issue = get_object_or_404(Issue, pk=id)
    all_copies = Copy.objects.select_related(
        'location', 'issue__edition__title'
    ).filter(canonical_query & Q(issue=id))

    def sort_key(c):
        loc = getattr(c.location, 'name_of_library_collection', '') if c.location else ''
        shelf = c.shelfmark or ''
        return (loc.lower(), shelf.lower())

    all_copies = sorted(all_copies, key=sort_key)

    return render(request, 'census/copy_list.html', {
        'all_copies': all_copies,
        'copy_count': len(all_copies),
        'selected_issue': selected_issue,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': selected_issue.edition.title
    })


# copy_data: Renders modal with details for a single copy.
def copy_data(request, copy_id):
    """Display detailed information for a single copy."""
    selected_copy = get_object_or_404(Copy, pk=copy_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'census/copy_modal.html', {'copy': selected_copy})
    return render(request, 'census/copy_detail.html', {'copy': selected_copy})


# copy_page: Standalone page for a copy, looked up by WC number.
def copy_page(request, wc_number):
    copy = get_object_or_404(Copy, wc_number=wc_number)
    return render(request, 'census/copy_page.html', {'copy': copy})


# cen_copy_modal: Alias for copy_data for backwards compatibility.
def cen_copy_modal(request, wc_number):
    """Display copy modal for a given wc_number."""
    selected_copy = get_object_or_404(Copy, wc_number=wc_number)
    selected_issue = selected_copy.issue
    all_copies = [selected_copy]
    return render(request, 'census/copy.html', {
        'all_copies': all_copies,
        'copy_count': 0,
        'selected_issue': selected_issue,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': selected_issue.edition.title
    })


# ------------------------------------------------------------------------------
# Issue list (per title)
# ------------------------------------------------------------------------------
# issue_list: Shows all issues for a given title, with edition and copy counts.
def issue_list(request, id):
    """Display all issues for a given title."""
    selected_title = get_object_or_404(Title, pk=id)
    editions = selected_title.edition_set.all()
    issues = [issue for ed in editions for issue in ed.issue_set.all()]
    issues.sort(key=lambda i: (
        int(i.edition.edition_number) if i.edition.edition_number.isdigit() else float('inf'),
        i.start_date,
        i.end_date,
        i.stc_wing
    ))
    # Sort editions for display (if used in play-title icons)
    editions = sorted(editions, key=lambda ed: title_sort_key(ed.title))
    copy_count = Copy.objects.filter(
        canonical_query,
        issue__id__in=[i.id for i in issues]
    ).count()
    return render(request, 'census/issue_list.html', {
        'icon_path': 'census/images/generic-title-icon.png',
        'editions': editions,
        'issues': issues,
        'title': selected_title,
        'copy_count': copy_count,
    })


# ------------------------------------------------------------------------------
# About / static pages
# ------------------------------------------------------------------------------
# about: Renders the about page and other static pages, pulling content from the StaticPageText model and replacing placeholders with dynamic values.
def about(request, viewname='about'):
    """Display the about page with census statistics."""
    from django.urls import reverse
    from . import models  # ensure models is imported if not already

    template = loader.get_template('census/about.html')
    copy_count = models.Copy.objects.filter(canonical_query & Q(fragment=False)).count()
    fragment_copy_count = models.Copy.objects.filter(fragment=True).count()
    facsimile_copy_count = models.Copy.objects.filter(
        ~Q(digital_facsimile_url=None) & ~Q(digital_facsimile_url='')
    ).count()
    if copy_count > 0:
        facsimile_copy_percent = round(100 * facsimile_copy_count / copy_count)
    else:
        facsimile_copy_percent = 0

    # Robust context for all likely-used placeholders in StaticPageText/about
    pre_render_context = {
        'copy_count': str(copy_count),
        'verified_copy_count': str(models.Copy.objects.filter(verified_query).count()),
        'unverified_copy_count': str(models.Copy.objects.filter(unverified_query).count()),
        'current_date': '{d:%d %B %Y}'.format(d=datetime.now()),
        'today': '{d:%d %B %Y}'.format(d=datetime.now()),  # alias for {today}
        'fragment_copy_count': str(fragment_copy_count),
        'facsimile_copy_count': str(facsimile_copy_count),
        'facsimile_count': str(facsimile_copy_count),  # alias for {facsimile_count}
        'facsimile_copy_percent': '{}%'.format(facsimile_copy_percent),
        'facsimile_percent': '{}%'.format(facsimile_copy_percent),  # alias for {facsimile_percent}
        'estc_copy_count': str(models.Copy.objects.filter(from_estc=True).count()),
        'non_estc_copy_count': str(models.Copy.objects.filter(from_estc=False).count()),
        'search_url': reverse('search'),
        'csv_url': reverse('location_copy_count_csv_export'),
        'homepage_url': reverse('homepage'),
        'about_url': reverse('about'),
        'contact_url': reverse('contact'),
        'blog_url': 'https://blog.wheatleycensus.org/',
        'advisoryboard_url': reverse('advisoryboard'),
        'references_url': reverse('references'),
        # Add more keys here as needed for future static text placeholders
    }

    content = [s.content.format(**pre_render_context)
               for s in models.StaticPageText.objects.filter(viewname=viewname)]
    context = {
        'content': content,
    }
    return HttpResponse(template.render(context, request))

# ------------------------------------------------------------------------------
# CSV exports
# ------------------------------------------------------------------------------
# location_copy_count_csv_export: Exports a CSV of locations and their copy counts.
def location_copy_count_csv_export(request):
    qs = Copy.objects.values('location').annotate(total=Count('location'))
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="census_location_copy_count.csv"'
    w = csv.writer(resp)
    w.writerow(['Location', 'Number of Copies'])
    for row in qs:
        loc = Location.objects.filter(pk=row['location']).first()
        w.writerow([loc.name_of_library_collection if loc else 'Unknown', row['total']])
    return resp


# year_issue_copy_count_csv_export: Exports a CSV of issues and their copy counts.
def year_issue_copy_count_csv_export(request):
    qs = Copy.objects.values('issue').annotate(total=Count('issue'))
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="census_year_issue_copy_count.csv"'
    w = csv.writer(resp)
    w.writerow(['Year', 'Title', 'Number of Copies'])
    for row in qs:
        iss = Issue.objects.filter(pk=row['issue']).first()
        if iss:
            w.writerow([iss.start_date, iss.edition.title.title, row['total']])
    return resp


# export: Generic CSV export for groupby/aggregate queries.
def export(request, groupby, column, aggregate):
    agg = Sum if aggregate == 'sum' else Count
    try:
        qs = Copy.objects.values(groupby).annotate(agg=agg(column)).order_by(groupby)
    except Exception:
        raise Http404("Invalid groupby or aggregate")
    fn = f"census_{aggregate}_of_{column}_for_each_{groupby}.csv"
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="{fn}"'
    w = csv.writer(resp)
    w.writerow([groupby, f"{aggregate} of {column}"])
    for row in qs:
        w.writerow([row[groupby], row['agg']])
    return resp


# ------------------------------------------------------------------------------
# Autocomplete endpoints
# ------------------------------------------------------------------------------
# autofill_location: Returns location suggestions for autocomplete.
def autofill_location(request, query=None):
    """Autocomplete endpoint for locations."""
    if query is not None:
        location_matches = Location.objects.filter(name__icontains=query)
        match_object = {'matches': [m.name for m in location_matches]}
    else:
        match_object = {'matches': []}
    return JsonResponse(match_object)


# autofill_provenance: Returns provenance name suggestions for autocomplete.
def autofill_provenance(request, query=None):
    """Autocomplete endpoint for provenance names."""
    if query is not None:
        prov_matches = ProvenanceName.objects.filter(name__icontains=query)
        match_object = {'matches': [m.name for m in prov_matches]}
    else:
        match_object = {'matches': []}
    return JsonResponse(match_object)


# autofill_collection: Returns static collection choices for autocomplete.
def autofill_collection(request, query=None):
    """Autocomplete endpoint for collections."""
    collection = [
        {'label': 'With known early provenance (before 1700)', 'value': 'earlyprovenance'},
        {'label': 'With a known woman owner', 'value': 'womanowner'},
        {'label': 'With a known woman owner before 1800', 'value': 'earlywomanowner'},
        {'label': 'Includes marginalia', 'value': 'marginalia'},
        {'label': 'In an early sammelband', 'value': 'earlysammelband'}
    ]
    return JsonResponse({'matches': collection})


# get_collection: Helper to filter queryset by collection type.
def get_collection(copy_list, coll_name):
    """Get a filtered collection of copies based on collection name."""
    if coll_name == 'earlyprovenance':
        results = copy_list.filter(provenance_search_names__start_century='17')
        display = 'Copies with known early provenance (before 1700)'
    elif coll_name == 'womanowner':
        results = copy_list.filter(provenance_search_names__gender='F')
        display = 'Copies with a known woman owner'
    elif coll_name == 'earlywomanowner':
        results = copy_list.filter(
            Q(provenance_search_names__gender='F') &
            (Q(provenance_search_names__start_century='17') |
             Q(provenance_search_names__start_century='18'))
        )
        display = 'Copies with a known woman owner before 1800'
    elif coll_name == 'marginalia':
        results = copy_list.exclude(Q(marginalia='') | Q(marginalia=None))
        display = 'Copies that include marginalia'
    elif coll_name == 'earlysammelband':
        results = copy_list.filter(in_early_sammelband=True)
        display = 'Copies in an early sammelband'
    return results, display


# ------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------
# login_user: Handles user login.
def login_user(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user_account = authenticate(username=username, password=password)
        if user_account is not None:
            login(request, user_account)
            next_url = request.GET.get('next', '/admin/')
            return HttpResponseRedirect(next_url)
        return render(request, 'census/login.html', {'failed': True})
    return render(request, 'census/login.html', {'next': request.GET.get('next', '')})


# logout_user: Handles user logout.
def logout_user(request):
    """Handle user logout."""
    logout(request)
    return render(request, 'census/logout.html')

def detail(request, id):
    selected_title = get_object_or_404(Title, pk=id)
    if id == '5' or id == '6':
        editions = list(selected_title.edition_set.all())
        extra_ed = list(Title.objects.get(pk='39').edition_set.all())
        extra_ed[0].Edition_number = '3'
        editions.extend(extra_ed)
    else:
        editions = list(selected_title.edition_set.all())
    issues = [issue for ed in editions for issue in ed.issue_set.all()]
    issues.sort(key=issue_sort_key)
    copy_count = Copy.objects.filter(issue__id__in=[i.id for i in issues]).count()
    context = {
        'icon_path': get_icon_path(selected_title),
        'editions': editions,
        'issues': issues,
        'title': selected_title,
        'copy_count': copy_count,
    }
    return render(request, 'census/detail.html', context)

def copy(request, id):
    selected_issue = get_object_or_404(Issue, pk=id)
    all_copies = Copy.objects.filter(issue__id=id).order_by('location__name', 'Shelfmark')
    all_copies = sorted(all_copies, key=copy_sort_key)
    context = {
        'all_copies': all_copies,
        'selected_issue': selected_issue,
        'icon_path': get_icon_path(selected_issue.edition.title),
        'title': selected_issue.edition.title
    }
    return render(request, 'census/copy.html', context)

# Add this utility function for sorting issues

def issue_sort_key(issue):
    """Sort key for issues: edition number (numeric if possible), start_date, end_date, stc_wing."""
    try:
        ed_num = int(issue.edition.edition_number) if issue.edition.edition_number.isdigit() else float('inf')
    except Exception:
        ed_num = float('inf')
    return (
        ed_num,
        getattr(issue, 'start_date', 0),
        getattr(issue, 'end_date', 0),
        getattr(issue, 'stc_wing', '')
    )

def all_copies_list(request):
    """Display all copies across all issues, sorted by year, location, shelfmark."""
    all_copies = Copy.objects.select_related('location', 'issue__edition__title').all()
    def sort_key(c):
        year = getattr(c.issue, 'start_date', None)
        if year is None:
            year = 9999  # Put missing years at the end
        loc = getattr(c.location, 'name_of_library_collection', '') if c.location else ''
        shelf = c.shelfmark or ''
        return (year, loc.lower(), shelf.lower())
    all_copies = sorted(all_copies, key=sort_key)
    return render(request, 'census/all_copies_list.html', {
        'all_copies': all_copies,
        'copy_count': len(all_copies),
        'icon_path': 'census/images/generic-title-icon.png',
    })