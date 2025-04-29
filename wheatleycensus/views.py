# marlowecensus/views.py

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.contrib.auth import logout, authenticate, login
from django.db.models import Q, Count, Sum
from datetime import datetime
import csv

from . import models
from .models import Title


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def strip_article(s):
    """
    If passed a Title instance, pull out its `.title` string first.
    Then drop any leading 'A ', 'An ', or 'The '.
    """
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
    except ValueError:
        a, b = 0, 0
    return (a, b)


# ------------------------------------------------------------------------------
# Homepage & Search
# ------------------------------------------------------------------------------
def homepage(request):
    tpl = loader.get_template('census/frontpage.html')
    titles = list(models.Title.objects.all())

    # sort first by embedded year, then by title (minus leading article)
    def extract_year(t):
        import re
        m = re.search(r'\b(\d{4})\b', t.title)
        return int(m.group(1)) if m else 9999

    titles.sort(key=lambda t: (extract_year(t), strip_article(t).lower()))
    rows = [titles[i:i+5] for i in range(0, len(titles), 5)]

    return HttpResponse(tpl.render({
        'titlerows': rows,
        'icon_path': 'census/images/generic-title-icon.png'
    }, request))


def search(request, field=None, value=None, order=None):
    tpl = loader.get_template('census/search-results.html')
    field = field or request.GET.get('field')
    value = value or request.GET.get('value')
    order = order or request.GET.get('order')

    base_q = Q(verification='U') | Q(verification='V') | Q(verification__isnull=True)
    qs = models.Copy.objects.filter(base_q)

    display_field, display_value = field, value

    # --- Filtering by field ---
    if field == 'keyword' or (not field and value):
        display_field = 'Keyword Search'
        q = (
            Q(marginalia__icontains=value) |
            Q(binding__icontains=value) |
            Q(backend_notes__icontains=value) |
            Q(prov_info__icontains=value) |
            Q(bibliography__icontains=value) |
            Q(provenance_records__provenance_name__name__icontains=value)
        )
        result_list = qs.filter(q)

    elif field == 'year' and value:
        display_field = 'Year'
        yr = convert_year_range(value)
        if yr:
            start, end = yr
            result_list = qs.filter(
                issue__start_date__lte=end,
                issue__end_date__gte=start
            )
        else:
            result_list = qs.filter(issue__year__icontains=value)

    elif field == 'location' and value:
        display_field = 'Location'
        result_list = qs.filter(
            location__name_of_library_collection__icontains=value
        )

    elif field == 'census_id' and value:
        display_field = 'WC'
        result_list = qs.filter(wc_number=value)

    elif field == 'provenance_name' and value:
        display_field = 'Provenance Name'
        result_list = qs.filter(
            provenance_records__provenance_name__name__icontains=value
        )

    elif field == 'unverified':
        display_field = 'Unverified'
        display_value = 'All'
        result_list = qs.filter(verification='U')

    elif field == 'ghosts':
        display_field = 'Ghosts'
        display_value = 'All'
        result_list = models.Copy.objects.filter(verification='F')

    else:
        result_list = qs.none()

    # --- Sorting ---
    if not order:
        order = 'date'

    if order == 'date':
        result_list = sorted(
            result_list,
            key=lambda c: (
                int(c.issue.start_date or 0),
                strip_article(c.issue.edition.title).lower(),
                strip_article(c.location.name_of_library_collection or '').lower()
            )
        )
    elif order == 'title':
        result_list = sorted(
            result_list,
            key=lambda c: (
                strip_article(c.issue.edition.title).lower(),
                int(c.issue.start_date or 0)
            )
        )
    elif order == 'location':
        result_list = sorted(
            result_list,
            key=lambda c: (
                strip_article(c.location.name_of_library_collection or '').lower(),
                int(c.issue.start_date or 0)
            )
        )
    elif order == 'stc':
        result_list = sorted(
            result_list,
            key=lambda c: (
                c.issue.year or '',
                strip_article(c.location.name_of_library_collection or '').lower()
            )
        )
    elif order.upper() in ('WC', 'CENSUS_ID'):
        result_list = sorted(result_list, key=copy_census_id_sort_key)

    return HttpResponse(tpl.render({
        'icon_path': 'census/images/generic-title-icon.png',
        'result_list': result_list,
        'copy_count': len(result_list),
        'field': field,
        'value': value,
        'display_field': display_field,
        'display_value': display_value,
    }, request))


# ------------------------------------------------------------------------------
# Copy listings & detail modals
# ------------------------------------------------------------------------------
def copy_list(request, id):
    tpl = loader.get_template('census/copy_list.html')
    issue = get_object_or_404(models.Issue, pk=id)
    qs = models.Copy.objects.filter(
        Q(verification='U') | Q(verification='V') | Q(verification__isnull=True),
        issue=id
    )
    copies = sorted(qs, key=copy_census_id_sort_key)

    return HttpResponse(tpl.render({
        'all_copies': copies,
        'copy_count': len(copies),
        'selected_issue': issue,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': issue.edition.title,
    }, request))


def copy_data(request, copy_id):
    tpl = loader.get_template('census/copy_modal.html')
    copy = get_object_or_404(models.Copy, pk=copy_id)
    return HttpResponse(tpl.render({'copy': copy}, request))


def copy_page(request, wc_number):
    """
    Stand‐alone page for /wc/<n>/ that auto‐opens the same modal
    used in the copy_list view.
    """
    copy = get_object_or_404(models.Copy, wc_number=wc_number)
    return render(request, 'census/copy_page.html', {
        'copy': copy,
    })


# ------------------------------------------------------------------------------
# Issue list (per title)
# ------------------------------------------------------------------------------
def issue_list(request, id):
    tpl = loader.get_template('census/issue_list.html')
    title = get_object_or_404(models.Title, pk=id)
    editions = title.edition_set.all()
    issues = [iss for ed in editions for iss in ed.issue_set.all()]
    issues.sort(key=lambda i: (
        int(i.edition.edition_number) if i.edition.edition_number.isdigit() else float('inf'),
        i.start_date, i.end_date
    ))
    copy_count = models.Copy.objects.filter(
        Q(verification='U') | Q(verification='V') | Q(verification__isnull=True),
        issue__in=issues
    ).count()

    return HttpResponse(tpl.render({
        'editions': editions,
        'issues': issues,
        'copy_count': copy_count,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': title,
    }, request))


# ------------------------------------------------------------------------------
# About / static pages
# ------------------------------------------------------------------------------
def about(request):
    base_q = Q(verification='U') | Q(verification='V') | Q(verification__isnull=True)
    copy_count = models.Copy.objects.filter(base_q, fragment=False).count()
    facsimile_count = models.Copy.objects.exclude(
        Q(digital_facsimile_url='') | Q(digital_facsimile_url=None)
    ).count()
    facsimile_percent = f"{round(100 * facsimile_count / copy_count)}%" if copy_count else "0%"

    return render(request, 'census/about.html', {
        'copy_count': copy_count,
        'facsimile_count': facsimile_count,
        'facsimile_percent': facsimile_percent,
        'unverified_count': models.Copy.objects.filter(verification='U').count(),
        'today': datetime.now().strftime("%d %B %Y"),
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
