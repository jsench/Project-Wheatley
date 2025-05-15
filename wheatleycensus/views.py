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
# Utility function for icon path
# ------------------------------------------------------------------------------
def get_icon_path(title_id):
    # Returns a generic icon path for all titles (customize as needed)
    return 'census/images/generic-title-icon.png'


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
# Utility functions for string manipulation, sorting, and year range parsing.
def strip_article(s):
    if isinstance(s, Title):
        s = s.title or ''
    if not isinstance(s, str):
        return ''
    for a in ('a ', 'A ', 'an ', 'An ', 'the ', 'The '):
        if s.startswith(a):
            return s[len(a):]
    return s


def convert_year_range(year):
    if '-' in year:
        start, end = [n.strip() for n in year.split('-', 1)]
        if len(start) == 4 and start.isdigit() and len(end) == 4 and end.isdigit():
            return int(start), int(end)
    elif len(year) == 4 and year.isdigit():
        return int(year), int(year)
    return False


def copy_census_id_sort_key(c):
    try:
        parts = (c.wc_number or "0").split('.', 1)
        a = int(parts[0])
        b = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, TypeError):
        a, b = 0, 0
    return (a, b)


def copy_sort_key(c):
    key_loc = strip_article(c.location.name_of_library_collection or '').lower()
    key_shelf = c.shelfmark or ''
    return (key_loc, key_shelf)


# ------------------------------------------------------------------------------
# Homepage & Search
# ------------------------------------------------------------------------------
# homepage: Renders the front page with a grid of titles.
def homepage(request):
    tpl = loader.get_template('census/frontpage.html')
    titles = list(Title.objects.all())

    def extract_year(t):
        import re
        m = re.search(r'\b(\d{4})\b', t.title or '')
        return int(m.group(1)) if m else 9999

    titles.sort(key=lambda t: (extract_year(t), strip_article(t).lower()))
    rows = [titles[i:i+5] for i in range(0, len(titles), 5)]

    return HttpResponse(tpl.render({
        'titlerows': rows,
        'icon_path': 'census/images/generic-title-icon.png'
    }, request))


# search: Unified search endpoint for filtering copies by location, keyword, provenance, gender, or census ID.
def search(request):
    """
    Unified search endpoint.  Supports GET params:
      - field:       one of ['location', 'keyword', 'provenance_name', 'gender', 'census_id']
      - value:       search term
      - page:        page number for pagination
    """
    field = request.GET.get('field', '').strip()
    value = request.GET.get('value', '').strip()

    # Base queryset: only "real" copies
    qs = Copy.objects.filter(
        Q(verification='U') |
        Q(verification='V') |
        Q(verification__isnull=True)
    )

    # Apply the chosen filter
    if field == 'location' and value:
        qs = qs.filter(location__name_of_library_collection__icontains=value)

    elif field == 'keyword' and value:
        qs = qs.filter(
            Q(issue__edition__title__icontains=value) |
            Q(marginalia__icontains=value) |
            Q(binding__icontains=value) |
            Q(backend_notes__icontains=value)
        )

    elif field == 'provenance_name' and value:
        qs = qs.filter(
            provenance_records__provenance_name__name__icontains=value
        )

    elif field == 'gender' and value:
        # Expect value to be "M" or "F" (or "male"/"female")
        gender_code = value[0].upper()
        qs = qs.filter(
            provenance_records__provenance_name__gender=gender_code
        )

    elif field == 'census_id' and value:
        qs = qs.filter(wc_number__iexact=value)
        # If exactly one result, redirect to the copy modal page
        if qs.count() == 1:
            copy = qs.first()
            return HttpResponseRedirect(f"/wc/{copy.wc_number}/")

    else:
        # If no valid filter, return empty to avoid dumping everything
        qs = qs.none()

    # Ordering — you can customize this as you like
    qs = qs.order_by('wc_number')

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'census/search-results.html', {
        'page_obj':      page_obj,
        'copy_count':    qs.count(),
        'field':         field,
        'value':         value,
        'display_field': field.replace('_', ' ').title(),
        'display_value': value or 'All',
        'icon_path': 'census/images/generic-title-icon.png',
    })


# search_results: (Legacy) Search endpoint for filtering by query params.
def search_results(request):
    qs = Copy.objects.select_related('location', 'issue__edition').all()

    q = request.GET.get('q')
    if q:
        qs = qs.filter(issue__edition__title__icontains=q)

    year = request.GET.get('year')
    if year:
        qs = qs.filter(issue__year=year)

    provenance = request.GET.get('provenance')
    if provenance:
        qs = qs.filter(location__name_of_library_collection__icontains=provenance)

    author = request.GET.get('author')
    if author:
        qs = qs.filter(issue__edition__author__icontains=author)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'census/search-results.html', {
        'page_obj': page_obj,
        'field': request.GET.get('field', ''),
        'display_field': request.GET.get('field', '').capitalize(),
        'display_value': request.GET.get('value', 'All'),
        'copy_count': qs.count(),
    })

canonical_query   = Q(verification='U') | Q(verification='V')
unverified_query  = Q(verification='U')
verified_query    = Q(verification='V')
false_query       = Q(verification='F')    # ← add this line
# ------------------------------------------------------------------------------
# Copy listings & detail modals
# ------------------------------------------------------------------------------
# copy_list: Shows all copies for a given Issue.
def copy_list(request, id):
    """
    Show all copies for a given Issue (id).
    """
    canonical_query = Q(verification='U') | Q(verification='V') | Q(verification__isnull=True)
    selected_issue = get_object_or_404(Issue, pk=id)
    qs = Copy.objects.filter(canonical_query, issue=id)
    all_copies = sorted(qs, key=copy_census_id_sort_key)
    context = {
        'all_copies': all_copies,
        'copy_count': len(all_copies),
        'selected_issue': selected_issue,
        'icon_path': get_icon_path(selected_issue.edition.title.id),
        'title': selected_issue.edition.title,
    }
    return render(request, 'census/copy_list.html', context)


# copy_data: Renders modal with details for a single copy.
def copy_data(request, copy_id):
    copy = get_object_or_404(Copy, pk=copy_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'census/copy_modal.html', {'copy': copy})
    return render(request, 'census/copy_detail.html', {'copy': copy})


# copy_page: Standalone page for a copy, looked up by WC number.
def copy_page(request, wc_number):
    copy = get_object_or_404(Copy, wc_number=wc_number)
    return render(request, 'census/copy_page.html', {'copy': copy})


# cen_copy_modal: Alias for copy_data for backwards compatibility.
def cen_copy_modal(request, census_id):
    """
    Alias for copy_data (for backwards compatibility on some links).
    """
    return copy_data(request, census_id)


# ------------------------------------------------------------------------------
# Issue list (per title)
# ------------------------------------------------------------------------------
# issue_list: Shows all issues for a given title, with edition and copy counts.
def issue_list(request, id):
    title = get_object_or_404(Title, pk=id)
    editions = title.edition_set.all()
    issues = [iss for ed in editions for iss in ed.issue_set.all()]
    issues.sort(key=lambda i: (
        int(i.edition.edition_number) if i.edition.edition_number.isdigit() else float('inf'),
        i.start_date, i.end_date
    ))
    copy_count = Copy.objects.filter(
        Q(verification='U') | Q(verification='V') | Q(verification__isnull=True),
        issue__in=issues
    ).count()

    return render(request, 'census/issue_list.html', {
        'editions': editions,
        'issues': issues,
        'copy_count': copy_count,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': title,
    })


# ------------------------------------------------------------------------------
# About / static pages
# ------------------------------------------------------------------------------
# about: Renders the about page and other static pages, pulling content from the StaticPageText model and replacing placeholders with dynamic values.
def about(request, viewname='about'):
    base_q = Q(verification='U') | Q(verification='V') | Q(verification__isnull=True)

    copy_count = Copy.objects.filter(base_q, fragment=False).count()
    facsimile_count = Copy.objects.exclude(
        Q(digital_facsimile_url='') | Q(digital_facsimile_url=None)
    ).count()
    facsimile_percent = f"{round(100 * facsimile_count / copy_count)}%" if copy_count else "0%"

    unverified_count = Copy.objects.filter(verification='U').count()
    today = datetime.now().strftime("%d %B %Y")

    search_url = reverse('search') + '?field=unverified'
    csv_url = reverse('location_copy_count_csv_export')

    content = [
        s.content.replace('{copy_count}', str(copy_count))
                 .replace('{facsimile_count}', str(facsimile_count))
                 .replace('{facsimile_percent}', str(facsimile_percent))
                 .replace('{unverified_count}', str(unverified_count))
                 .replace('{today}', today)
                 .replace('{search_url}', search_url)
                 .replace('{csv_url}', csv_url)
        for s in StaticPageText.objects.filter(viewname='about')
    ]

    # Determine which static page to render
    if request.path.endswith('advisoryboard/'):
        return render(request, 'census/advisoryboard.html', {})
    elif request.path.endswith('references/'):
        return render(request, 'census/references.html', {})
    elif request.path.endswith('contact/'):
        return render(request, 'census/contact.html', {})
    else:
        return render(request, 'census/about.html', {
            'content': content,
            'copy_count': copy_count,
            'facsimile_count': facsimile_count,
            'facsimile_percent': facsimile_percent,
            'unverified_count': unverified_count,
            'today': today,
        })

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
    query = query or ""
    # 1) DB matches
    db_matches = Location.objects.filter(
        name_of_library_collection__icontains=query
    ).values_list('name_of_library_collection', flat=True)

    # 2) Static matches (states + countries)
    static_pool = US_STATES + WORLD_COUNTRIES
    static_matches = [
        name for name in static_pool
        if query.lower() in name.lower() and name not in db_matches
    ]

    # 3) Return combined, capped at e.g. 50 suggestions
    suggestions = list(db_matches) + static_matches
    return JsonResponse({'matches': suggestions[:50]})


# autofill_provenance: Returns provenance name suggestions for autocomplete.
def autofill_provenance(request, query=None):
    matches = ProvenanceName.objects.filter(name__icontains=query) if query else []
    return JsonResponse({'matches': [m.name for m in matches]})


# autofill_collection: Returns static collection choices for autocomplete.
def autofill_collection(request, query=None):
    choices = [
        {'label': 'With known early provenance (before 1700)', 'value': 'earlyprovenance'},
        {'label': 'With a known woman owner', 'value': 'womanowner'},
        {'label': 'With a known woman owner before 1800', 'value': 'earlywomanowner'},
        {'label': 'Includes marginalia', 'value': 'marginalia'},
        {'label': 'In an early sammelband', 'value': 'earlysammelband'},
    ]
    return JsonResponse({'matches': choices})


# get_collection: Helper to filter queryset by collection type.
def get_collection(qs, name):
    if name == 'earlyprovenance':
        return (
            qs.filter(provenance_records__provenance_name__start_century='17'),
            'Copies with known early provenance (before 1700)'
        )
    if name == 'womanowner':
        return (
            qs.filter(provenance_records__provenance_name__gender='F'),
            'Copies with a known woman owner'
        )
    if name == 'earlywomanowner':
        return (
            qs.filter(provenance_records__provenance_name__gender='F')
              .filter(Q(provenance_records__provenance_name__start_century__in=['17','18'])),
            'Copies with a known woman owner before 1800'
        )
    if name == 'marginalia':
        return (
            qs.exclude(Q(marginalia='') | Q(marginalia=None)),
            'Copies that include marginalia'
        )
    if name == 'earlysammelband':
        return (
            qs.filter(in_early_sammelband=True),
            'Copies in an early sammelband'
        )
    return (qs.none(), 'Unknown collection')


# ------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------
# login_user: Handles user login.
def login_user(request):
    tpl = loader.get_template('census/login.html')
    if request.method == 'POST':
        u = request.POST.get('username', '')
        p = request.POST.get('password', '')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            return HttpResponseRedirect(request.GET.get('next', '/admin/'))
        return HttpResponse(tpl.render({'failed': True}, request))
    return HttpResponse(tpl.render({'next': request.GET.get('next', '')}, request))


# logout_user: Handles user logout.
def logout_user(request):
    tpl = loader.get_template('census/logout.html')
    logout(request)
    return HttpResponse(tpl.render({}, request))

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
        'icon_path': get_icon_path(id),
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
        'icon_path': get_icon_path(selected_issue.edition.title.id),
        'title': selected_issue.edition.title
    }
    return render(request, 'census/copy.html', context)

def draft_copy_data(request, copy_id):
    template = loader.get_template('census/copy_modal.html')
    selected_copy = Copy.objects.filter(pk=copy_id)
    if selected_copy:
        selected_copy = get_draft_if_exists(selected_copy[0])
    else:
        selected_copy = get_object_or_404(Copy, pk=copy_id)
    context = {"copy": selected_copy}
    return render(request, 'census/copy_modal.html', context)

@login_required()
def update_draft_copy(request, id):
    canonical_copy = get_object_or_404(Copy, pk=id)
    selected_copy = get_draft_if_exists(canonical_copy)
    init_fields = ['Shelfmark', 'Local_Notes', 'prov_info', 'Height', 'Width', 'Marginalia', 'Binding', 'Binder']
    data = {f: getattr(selected_copy, f) for f in init_fields}
    if request.method == 'POST':
        copy_form = forms.LibrarianCopySubmissionForm(request.POST)
        if copy_form.is_valid():
            copy_form_data = copy_form.save(commit=False)
            draft_copy = get_or_create_draft(canonical_copy)
            for f in init_fields:
                setattr(draft_copy, f, getattr(copy_form_data, f))
            draft_copy.save()
            return HttpResponseRedirect(reverse('librarian_validate2'))
    else:
        copy_form = forms.LibrarianCopySubmissionForm(initial=data)
    context = {
        'form': copy_form,
        'copy': selected_copy,
        'icon_path': get_icon_path(selected_copy.issue.edition.title.id)
    }
    return render(request, 'census/copy_submission.html', context)

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler400(request, exception):
    return render(request, '400.html', status=400)