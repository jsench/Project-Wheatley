from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.template import loader
from django.contrib.auth import logout, authenticate, login
from django.db.models import Q, Count, Sum
from datetime import datetime
import csv
from . import models


## UTILITY FUNCTIONS ##
def strip_article(s):
    articles = ['a ', 'A ', 'an ', 'An ', 'the ', 'The ']
    for a in articles:
        if s.startswith(a):
            return s.replace(a, '', 1)
    else:
        return s

def convert_year_range(year):
    if '-' in year:
        start, end = [n.strip() for n in year.split('-', 1)]
        if len(start) == 4 and start.isdigit() and len(end) == 4 and end.isdigit():
            return int(start), int(end)
    elif len(year) == 4 and year.isdigit():
        return int(year), int(year)
    return False

def title_sort_key(title_object):
    title = title_object.title

    if title and title[0].isdigit():
        title = title.split()
        return strip_article(' '.join(title[1:] + [title[0]]))
    else:
        return strip_article(title)

def issue_sort_key(i):
    ed_number = i.edition.edition_number
    ed_idx = int(ed_number) if ed_number.isdigit() else float('inf')
    return (ed_idx, i.stc_wing)

def issue_date_sort_key(issue):
    return int(issue.start_date)

def issue_stc_sort_key(issue):
    return issue.stc_wing

def copy_sort_key(c):
    census_id_a, census_id_b = copy_census_id_sort_key(c)
    return (copy_location_sort_key(c),
            copy_shelfmark_sort_key(c),
            census_id_a,
            census_id_b)

def copy_date_sort_key(c):
    return int(c.issue.start_date)

def copy_census_id_sort_key(c):
    census_id = c.census_id if c.census_id is not None else ''
    census_id_a = 0
    census_id_b = 0
    try:
        if '.' in census_id:
            census_id_a, census_id_b = census_id.split('.')
            census_id_a, census_id_b = int(census_id_a), int(census_id_b)
        else:
            census_id_a = int(census_id)
    except ValueError:
        pass
    return (census_id_a, census_id_b)

def copy_location_sort_key(c):
    if c.location is not None:
        name = c.location.name
    else:
        name = ''
    return strip_article(name if name else '')

def copy_shelfmark_sort_key(c):
    sm = c.Shelfmark
    return sm if sm else ''

def detail_sort_key(issue):
    ed_number = issue.edition.edition_number
    ed_idx = int(ed_number) if ed_number.isdigit() else float('inf')
    return (ed_idx, issue.start_date, issue.end_date, issue.stc_wing)

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
    return (copy.issue.stc_wing,
            copy_location_sort_key(copy))


## Defining queries for verification status of copies ##
canonical_query = (Q(verification='U') |
                   Q(verification='V'))
unverified_query = Q(verification='U')
verified_query = Q(verification='V')
false_query = Q(verification='F')


## VIEW FUNCTIONS ##
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
        'icon_path': 'census/images/generic-title-icon.png'
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

def about(request, viewname='about'):
    template = loader.get_template('census/about.html')
    copy_count = models.Copy.objects.filter(canonical_query & Q(fragment=False)).count()
    fragment_copy_count = models.Copy.objects.filter(fragment=True).count()
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
        'fragment_copy_count': str(fragment_copy_count),
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
            iss_obj.stc_wing,
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
            request.GET.order = 'location'
            order = 'location'
    elif field == 'ghosts':
        display_field = 'Ghosts'
        display_value = 'All'
        result_list = models.Copy.objects.filter(false_query)
    elif field == 'collection':
        result_list, display_field = get_collection(copy_list, value)
        display_value = 'All'
    else:
        result_list = models.Copy.objects.none()

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
    elif order == 'MC':
        result_list = sorted(result_list, key=copy_cen_sort_key)
    context = {
        'icon_path': 'census/images/generic-title-icon.png',
        'value': value,
        'field': field,
        'display_value': display_value,
        'display_field': display_field,
        'result_list': result_list,
        'copy_count': len(result_list)
    }

    return HttpResponse(template.render(context, request))

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

def autofill_collection(request, query=None):
    collection = [{'label': 'With known early provenance (before 1700)', 'value': 'earlyprovenance'},
                  {'label': 'With a known woman owner', 'value': 'womanowner'},
                  {'label': 'With a known woman owner before 1800', 'value': 'earlywomanowner'},
                  {'label': 'Includes marginalia', 'value': 'marginalia'},
                  {'label': 'In an early sammelband', 'value': 'earlysammelband'}]
    return JsonResponse({'matches': collection})

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

def copy(request, id):
    selected_issue = get_object_or_404(models.Issue, pk=id)
    all_copies = models.Copy.objects.filter(canonical_query & Q(issue = id)).order_by('location__name', 'Shelfmark')
    all_copies = sorted(all_copies, key=copy_sort_key)
    template = loader.get_template('census/copy.html')
    context = {
        'all_copies': all_copies,
        'copy_count': len(all_copies),
        'selected_issue': selected_issue,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': selected_issue.edition.title
    }
    return HttpResponse(template.render(context, request))

def copy_data(request, copy_id):
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

def detail(request, id):
    selected_title = get_object_or_404(models.Title, pk=id)
    editions = list(selected_title.edition_set.all())
    issues = [issue for ed in editions for issue in ed.issue_set.all()]
    issues.sort(key=detail_sort_key)
    copy_count = models.Copy.objects.filter(issue__id__in=[i.id for i in issues]).filter(canonical_query).count()
    template = loader.get_template('census/detail.html')
    context = {
        'icon_path': 'census/images/generic-title-icon.png',
        'editions': editions,
        'issues': issues,
        'title': selected_title,
        'copy_count': copy_count,
    }
    return HttpResponse(template.render(context, request))

def cen_copy_modal(request, census_id):
    selected_copy = get_object_or_404(models.Copy, census_id=census_id)
    selected_issue = selected_copy.issue
    all_copies = [selected_copy]
    template = loader.get_template('census/copy.html')
    context = {
        'all_copies': all_copies,
        'copy_count': 0,
        'selected_issue': selected_issue,
        'icon_path': 'census/images/generic-title-icon.png',
        'title': selected_issue.edition.title
    }
    return HttpResponse(template.render(context, request))
