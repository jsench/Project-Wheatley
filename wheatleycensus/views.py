# wheatleycensus/views.py


from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.contrib.auth import logout, authenticate, login
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from .constants import US_STATES, WORLD_COUNTRIES
from .models import Copy, Issue, Title, Location, ProvenanceName, models  # adjust if your models module defines others
from datetime import datetime
import csv


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
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


def search(request):
    """
    Unified search endpoint.  Supports GET params:
      - field:       one of ['location', 'keyword', 'provenance_name', 'gender', 'census_id']
      - value:       search term
      - page:        page number for pagination
    """
    field = request.GET.get('field', '').strip()
    value = request.GET.get('value', '').strip()

    # Base queryset: only “real” copies
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

    else:
        # If no valid filter, return empty to avoid dumping everything
        qs = qs.none()

    # Ordering — you can customize this as you like
    qs = qs.order_by('issue__start_date', 'issue__edition__title')

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


# ------------------------------------------------------------------------------
# Copy listings & detail modals
# ------------------------------------------------------------------------------
canonical_query = (
    Q(verification='U') |
    Q(verification='V') |
    Q(verification__isnull=True)
)


def copy_list(request, id):
    """
    Show all copies for Issue `id`.
    """
    # 1) Look up the issue (404 if missing)
    selected_issue = get_object_or_404(models.Issue, pk=id)

    # 2) Filter only “real” copies for that issue
    qs = (
        models.Copy.objects
        .filter(canonical_query, issue_id=id)
        .order_by('location__name_of_library_collection', 'shelfmark')
    )

    # 3) If you still need your custom sort key:
    all_copies = sorted(qs, key=copy_sort_key)

    # 4) Render with your copy_list.html template
    return render(request, 'census/copy_list.html', {
        'all_copies':     all_copies,
        'copy_count':     len(all_copies),
        'selected_issue': selected_issue,
        'icon_path':      'census/images/generic-title-icon.png',
        'title':          selected_issue.edition.title,
    })


def copy_data(request, copy_id):
    """
    AJAX endpoint: render details for one Copy in a modal.
    """
    copy = get_object_or_404(models.Copy, pk=copy_id)
    return render(request, 'census/copy_modal.html', {
        'copy': copy
    })
# ------------------------------------------------------------------------------
# Issue list (per title)
# ------------------------------------------------------------------------------
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
def about(request):
    base_q = Q(verification='U') | Q(verification='V') | Q(verification__isnull=True)

    copy_count = Copy.objects.filter(base_q, fragment=False).count()
    facsimile_count = Copy.objects.exclude(
        Q(digital_facsimile_url='') | Q(digital_facsimile_url=None)
    ).count()
    facsimile_percent = f"{round(100 * facsimile_count / copy_count)}%" if copy_count else "0%"

    unverified_count = Copy.objects.filter(verification='U').count()

    today = datetime.now().strftime("%d %B %Y")

    return render(request, 'census/about.html', {
        'copy_count': copy_count,
        'facsimile_count': facsimile_count,
        'facsimile_percent': facsimile_percent,
        'unverified_count': unverified_count,
        'today': today,
    })
# ------------------------------------------------------------------------------
# CSV exports
# ------------------------------------------------------------------------------
def location_copy_count_csv_export(request):
    qs = models.Copy.objects.values('location').annotate(total=Count('location'))
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="census_location_copy_count.csv"'
    w = csv.writer(resp)
    w.writerow(['Location', 'Number of Copies'])
    for row in qs:
        loc = models.Location.objects.filter(pk=row['location']).first()
        w.writerow([loc.name_of_library_collection if loc else 'Unknown', row['total']])
    return resp


def year_issue_copy_count_csv_export(request):
    qs = models.Copy.objects.values('issue').annotate(total=Count('issue'))
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="census_year_issue_copy_count.csv"'
    w = csv.writer(resp)
    w.writerow(['Year', 'Title', 'Number of Copies'])
    for row in qs:
        iss = models.Issue.objects.filter(pk=row['issue']).first()
        if iss:
            w.writerow([iss.start_date, iss.edition.title.title, row['total']])
    return resp


def export(request, groupby, column, aggregate):
    agg = Sum if aggregate == 'sum' else Count
    try:
        qs = models.Copy.objects.values(groupby).annotate(agg=agg(column)).order_by(groupby)
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
def autofill_location(request, query=None):
    matches = models.Location.objects.filter(name_of_library_collection__icontains=query) if query else []
    return JsonResponse({'matches': [m.name_of_library_collection for m in matches]})


def autofill_provenance(request, query=None):
    matches = models.ProvenanceName.objects.filter(name__icontains=query) if query else []
    return JsonResponse({'matches': [m.name for m in matches]})


def autofill_collection(request, query=None):
    choices = [
        {'label': 'With known early provenance (before 1700)', 'value': 'earlyprovenance'},
        {'label': 'With a known woman owner', 'value': 'womanowner'},
        {'label': 'With a known woman owner before 1800', 'value': 'earlywomanowner'},
        {'label': 'Includes marginalia', 'value': 'marginalia'},
        {'label': 'In an early sammelband', 'value': 'earlysammelband'},
    ]
    return JsonResponse({'matches': choices})


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


def logout_user(request):
    tpl = loader.get_template('census/logout.html')
    logout(request)
    return HttpResponse(tpl.render({}, request))


# --------- constants ---------------#

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