from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template import loader
from . import models
from . import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login
from django.db.models import Q, Count, Sum
from django.urls import reverse
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime

import csv

canonical_query = (Q(verification='U') |
                   Q(verification='V'))

unverified_query = Q(verification='U')

verified_query = Q(verification='V')

false_query = Q(verification='F')


## UTILITY FUNCTIONS ##
# Eventually these should be moved into a separate util module.
def strip_article(s):
    articles = ['a ', 'A ', 'an ', 'An ', 'the ', 'The ']
    for a in articles:
        if s.startswith(a):
            return s.replace(a, '', 1)
    else:
        return s

def search_sort_date(copy):
    return (copy_date_sort_key(copy),
            title_sort_key(copy.issue.edition.title),
            copy_location_sort_key(copy))

def search_sort_title(copy):
    return (title_sort_key(copy.issue.edition.title),
            copy_date_sort_key(copy),
            copy_location_sort_key(copy))

def search_sort_location(copy):
    return (copy_location_sort_key(copy),
            copy_date_sort_key(copy),
            title_sort_key(copy.issue.edition.title))

def search_sort_stc(copy):
    return (copy.issue.STC_Wing,
            copy_location_sort_key(copy))

def issue_stc_sort_key(issue):
    return issue.STC_Wing

def copy_date_sort_key(c):
    return int(c.issue.start_date)

def issue_date_sort_key(issue):
    return int(issue.start_date)

def copy_cen_sort_key(c):
    cen = c.cen if c.cen is not None else ''
    cen_a = 0
    cen_b = 0

    try:
        if '.' in cen:
            cen_a, cen_b = cen.split('.')
            cen_a, cen_b = int(cen_a), int(cen_b)
        else:
            cen_a = int(cen)
    except ValueError:
        pass

    return (cen_a, cen_b)

def copy_location_sort_key(c):
    if c.location is not None:
        name = c.location.name
    else:
        name = ''
    return strip_article(name if name else '')

def copy_shelfmark_sort_key(c):
    sm = c.Shelfmark
    return sm if sm else ''

def copy_sort_key(c):
    cen_a, cen_b = copy_cen_sort_key(c)
    return (copy_location_sort_key(c),
            copy_shelfmark_sort_key(c),
            cen_a,
            cen_b)

def title_sort_key(title_object):
    title = title_object.title

    if title and title[0].isdigit():
        title = title.split()
        return strip_article(' '.join(title[1:] + [title[0]]))
    else:
        return strip_article(title)

def issue_sort_key(i):
    ed_number = i.edition.Edition_number
    ed_idx = int(ed_number) if ed_number.isdigit() else float('inf')
    return (ed_idx, i.STC_Wing)

def convert_year_range(year):
    if '-' in year:
        start, end = [n.strip() for n in year.split('-', 1)]
        if len(start) == 4 and start.isdigit() and len(end) == 4 and end.isdigit():
            return int(start), int(end)
    elif len(year) == 4 and year.isdigit():
        return int(year), int(year)
    return False

## VIEW FUNCTIONS ##

def search(request, field=None, value=None, order=None):
    template = loader.get_template('census/search-results.html')
    field = field if field is not None else request.GET.get('field')
    value = value if value is not None else request.GET.get('value')
    order = order if order is not None else request.GET.get('order')
    copy_list = models.Copy.objects.filter(canonical_query)
    display_field = field
    display_value = value

    if field == 'keyword' or field is None and value:
        field = 'keyword'
        display_field = 'Keyword Search'
        query = (Q(Marginalia__icontains=value) |
                 Q(Binding__icontains=value) |
                 Q(Local_Notes__icontains=value) |
                 Q(prov_info__icontains=value) |
                 Q(bibliography__icontains=value) |
                 Q(provenance_search_names__name__icontains=value))
        result_list = copy_list.filter(query)
    elif field == 'stc' and value:
        display_field = 'STC / Wing'
        result_list = copy_list.filter(issue__STC_Wing__icontains=value)
    elif field == 'cen' and value:
        display_field = 'cen'
        result_list = copy_list.filter(cen=value)
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
            request.GET.order = 'location'
            order = 'location'
    elif field == 'ghosts':
        display_field = 'Ghosts'
        display_value = 'All'
        result_list = copy_list.filter(false_query)
    elif field == 'collection':
        result_list, display_field = get_collection(copy_list, value)
        display_value = 'All'
    else:
        result_list = models.Copy.objects.none()

    result_list = result_list.exclude(issue__edition__title__title='Comedies, Histories, and Tragedies')
    result_list = result_list.distinct()

    if order is None:
        request.GET.order = 'date'
        result_list = sorted(result_list, key=search_sort_date)
    elif order == 'date':
        result_list = sorted(result_list, key=search_sort_date)
    elif order == 'title':
        result_list = sorted(result_list, key=search_sort_title)
    elif order == 'location':
        result_list = sorted(result_list, key=search_sort_location)
    elif order == 'stc':
        result_list = sorted(result_list, key=search_sort_stc)
    elif order == 'cen':
        result_list = sorted(result_list, key=copy_cen_sort_key)

    context = {
        'icon_path': 'census/images/title_icons/generic-title-icon.png',
        'value': value,
        'field': field,
        'display_value': display_value,
        'display_field': display_field,
        'result_list': result_list,
        'copy_count': len(result_list)
    }

    return HttpResponse(template.render(context, request))

def get_collection(copy_list, coll_name):
    if coll_name == 'earlyprovenance':
        results = copy_list.filter(provenance_search_names__start_century='17')
        display = 'Copies with known early provenance (before 1700)'
    elif coll_name == 'womanowner':
        results = copy_list.filter(provenance_search_names__gender='F')
        display = 'Copies with a known woman owner'
    elif coll_name == 'earlywomanowner':
        results = copy_list.filter(Q(provenance_search_names__gender='F') &
                                   (Q(provenance_search_names__start_century='17') |
                                    Q(provenance_search_names__start_century='18')))
        display = 'Copies with a known woman owner before 1800'
    elif coll_name == 'marginalia':
        results = copy_list.exclude(Q(Marginalia='') | Q(Marginalia=None))
        display = 'Copies that include marginalia'
    elif coll_name == 'earlysammelband':
        results = copy_list.filter(in_early_sammelband=True)
        display = 'Copies in an early sammelband'

    return results, display

def autofill_collection(request, query=None):
    collection = [{'label': 'With known early provenance (before 1700)', 'value': 'earlyprovenance'},
                  {'label': 'With a known woman owner', 'value': 'womanowner'},
                  {'label': 'With a known woman owner before 1800', 'value': 'earlywomanowner'},
                  {'label': 'Includes marginalia', 'value': 'marginalia'},
                  {'label': 'In an early sammelband', 'value': 'earlysammelband'}]
    return JsonResponse({'matches': collection})

def autofill_location(request, query=None):
    if query is not None:
        location_matches = models.Location.objects.filter(name__icontains=query)
        match_object = {'matches': [m.name for m in location_matches]}
    else:
        match_object = {'matches': []}
    return JsonResponse(match_object)

def autofill_provenance(request, query=None):
    if query is not None:
        prov_matches = models.ProvenanceName.objects.filter(name__icontains=query)
        match_object = {'matches': [m.name for m in prov_matches]}
    else:
        match_object = {'matches': []}
    return JsonResponse(match_object)

'''WHERE WE ARE'''

def homepage(request):
    template = loader.get_template('census/frontpage.html')
    gridwidth = 5
    titlelist = models.Title.objects.all()
    titlelist = sorted(titlelist, key=title_sort_key)
    titlerows = [titlelist[i: i + gridwidth]
                 for i in range(0, len(titlelist), gridwidth)]
    context = {
        'frontpage': True,
        'titlelist': titlelist,
        'titlerows': titlerows,
        'icon_path': 'census/images/title_icons/generic-title-icon.png'
    }
    return HttpResponse(template.render(context, request))

def about(request, viewname='about'):
    template = loader.get_template('census/about.html')
    copy_count = models.Copy.objects.filter(canonical_query).count()
    facsimile_copy_count = models.Copy.objects.filter(
            ~Q(Digital_Facsimile_URL=None) & ~Q(Digital_Facsimile_URL='')
    ).count()
    if copy_count > 0:
        facsimile_copy_percent = round(100 * facsimile_copy_count / copy_count)
    else:
        facsimile_copy_percent = 0

    pre_render_context = {
        'copy_count': str(copy_count),
        'verified_copy_count': str(models.Copy.objects.filter(verified_query).count()),
        'unverified_copy_count': str(models.Copy.objects.filter(unverified_query).count()),
        'current_date': '{d:%d %B %Y}'.format(d=datetime.now()),
        'facsimile_copy_count': str(facsimile_copy_count),
        'facsimile_copy_percent': '{}%'.format(facsimile_copy_percent),
        'estc_copy_count': str(models.Copy.objects.filter(from_estc=True).count()),
        'non_estc_copy_count': str(models.Copy.objects.filter(from_estc=False).count()),
    }
    content = [s.content.format(**pre_render_context)
               for s in models.StaticPageText.objects.filter(viewname=viewname)]

    context =  {
        'content': content,
    }
    return HttpResponse(template.render(context, request))

def detail(request, id):
    selected_title = get_object_or_404(models.Title, pk=id)
    editions = list(selected_title.edition_set.all())
    issues = [issue for ed in editions for issue in ed.issue_set.all()]
    issues.sort(key=issue_date_sort_key)
    issues.sort(key=issue_stc_sort_key)
    copy_count = models.Copy.objects.filter(issue__id__in=[i.id for i in issues]).count()
    template = loader.get_template('census/detail.html')
    context = {
        'icon_path': 'census/images/title_icons/generic-title-icon.png',
        'editions': editions,
        'issues': issues,
        'title': selected_title,
        'copy_count': copy_count,
    }
    return HttpResponse(template.render(context, request))

# showing all copies for an issue
def copy(request, id):
    selected_issue = get_object_or_404(models.Issue, pk=id)
    print(models.Copy.objects.all())
    all_copies = models.Copy.objects.filter(canonical_query & Q(issue = id)).order_by('location__name', 'Shelfmark')
    all_copies = sorted(all_copies, key=copy_sort_key)
    template = loader.get_template('census/copy.html')
    context = {
        'all_copies': all_copies,
        'copy_count': len(all_copies),
        'selected_issue': selected_issue,
        'icon_path': 'census/images/title_icons/generic-title-icon.png',
        'title': selected_issue.edition.title
    }
    return HttpResponse(template.render(context, request))

'''def draft_copy_data(request, copy_id):
    # This is a little bit questionable, so I'm explaining in detail.

    # To avoid having a proliferation of endpoints for copies of
    # multiple kinds, we simplify by assuming the incoming ID is
    # a canonical copy, and getting the corresponding draft
    # information if it exists. Otherwise, no draft has been created
    # yet, and so we should return the original data, which is the only
    # existing "draft."

    # That makes perfect sense.

    # *However* ... sometimes it's necessary to ask for an existing draft
    # copy by its own ID instead of by the copy id. If the above
    # fails, we try to do that instead. This allows us to reuse several
    # templates that we would otherwise have to customize.

    template = loader.get_template('census/copy_modal.html')
    selected_copy = models.Copy.objects.filter(pk=copy_id)
    if selected_copy:
        selected_copy = get_draft_if_exists(selected_copy[0])
    else:
        selected_copy = models.DraftCopy.objects.get(pk=copy_id)

    context={"copy": selected_copy}

    return HttpResponse(template.render(context, request))'''

def copy_data(request, copy_id):
    # See above notes to `draft_copy_data`. Here, instead of
    # canonical -> draft, it's canonical -> false. But the essential
    # idea is the same; we get to reuse templates by cheating a
    # little bit here. In this case it's the `search_results`
    # template, which is also used to display false copies.

    template = loader.get_template('census/copy_modal.html')
    selected_copy = models.Copy.objects.filter(pk=copy_id)
    if not selected_copy:
        selected_copy = models.Copy.objects.filter(false_query).filter(pk=copy_id)

    if selected_copy:
        selected_copy = selected_copy[0]
    else:
        raise Http404('Selected copy does not exist')

    context={"copy": selected_copy}

    return HttpResponse(template.render(context, request))

def cen_copy_modal(request, cen):
    # This is almost identical to copy, above, but it accepts a CEN number
    # instead of an issue number, and if the CEN number is found, it
    # finds the issue, and displays the page for that issue. The
    # modal-display javascript then detects what has happened and
    # automatically displays the modal for the given copy.

    selected_copy = get_object_or_404(models.Copy, cen=cen)
    selected_issue = selected_copy.issue
    # all_copies = models.Copy.objects.filter(issue=selected_issue).order_by('location__name', 'Shelfmark')
    # all_copies = sorted(all_copies, key=copy_sort_key)
    all_copies = [selected_copy]
    template = loader.get_template('census/copy.html')
    context = {
        'all_copies': all_copies,
        'copy_count': 0,
        'selected_issue': selected_issue,
        'icon_path': 'census/images/title_icons/generic-title-icon.png',
        'title': selected_issue.edition.title
    }
    return HttpResponse(template.render(context, request))


def login_user(request):
    template = loader.get_template('census/login.html')
    if request.method=='POST':
        username = request.POST['username']
        password = request.POST['password']
        user_account = authenticate(username=username, password=password)
        if user_account is not None:
            login(request, user_account)
            next_url = '/admin/'
            return HttpResponseRedirect(next_url)
        else:
            return HttpResponse(template.render({'failed': True}, request))
    else:
        return HttpResponse(template.render({'next': request.GET.get('next', '')}, request))

def logout_user(request):
    template = loader.get_template('census/logout.html')
    logout(request)
    context = {}
    return HttpResponse(template.render(context,request))

#expected to be called when a new copy is submitted; displaying the copy info
def copy_info(request, copy_id):
    template = loader.get_template('census/copy_info.html')
    selected_copy = get_object_or_404(models.ChildCopy, pk=copy_id)
    selected_issue = selected_copy.issue
    selected_edition = selected_issue.edition
    context = {
        'selected_edition': selected_edition,
        'selected_copy': selected_copy,
    }
    return HttpResponse(template.render(context,request))

def location_copy_count_csv_export(request):
    locations = models.Copy.objects.all().values('location')
    locations = locations.annotate(total=Count('location')).order_by('location__name')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="census_location_copy_count.csv"'

    writer = csv.writer(response)
    writer.writerow(['Location', 'Number of Copies'])
    for loc in locations:
        writer.writerow([models.Location.objects.get(pk=loc['location']).name, loc['total']])

    return response

def year_issue_copy_count_csv_export(request):
    issues = models.Copy.objects.all().values('issue')
    issues = issues.annotate(total=Count('issue')).order_by('issue__start_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="census_year_issue_copy_count.csv"'

    writer = csv.writer(response)
    writer.writerow(['Year', 'STC/Wing', 'Title', 'Number of Copies'])
    for iss in issues:
        iss_obj = models.Issue.objects.get(pk=iss['issue'])
        writer.writerow([
            iss_obj.start_date,
            iss_obj.STC_Wing,
            iss_obj.edition.title.title,
            iss['total']
        ])

    return response

def export(request, groupby, column, aggregate):
    agg_model = (# Concat if aggregate == 'concatenation' else
                 Sum if aggregate == 'sum' else
                 Count)
    try:
        groups = models.Copy.objects.all().values(groupby)
    except:
        raise Http404('Invalid groupby column.')

    try:
        rows = groups.annotate(agg=agg_model(column)).order_by(groupby)
    except:
        raise Http404('Invalid aggregation column.')

    filename = 'census_{}_of_{}_for_each_{}.csv'
    filename = filename.format(aggregate, column, groupby)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    writer = csv.writer(response)
    writer.writerow([groupby, '{} of {}'.format(aggregate, column)])

    for row in rows:
        writer.writerow([row[groupby], row['agg']])

    return response
