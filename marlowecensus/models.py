from django.db import models
from django.conf import settings


### Main Site Operations ###

class StaticPageText(models.Model):
    content = models.TextField(null=True, blank=True, default=None)
    viewname = models.CharField(max_length=255, default='', null=True, blank=True)

    def __str__(self):
        return self.viewname
    class Meta:
        verbose_name_plural = "Static Pages"


### Core Data Tables ###

class Location(models.Model):
    LOCATION_CHOICES = [
        # US States
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'),
        ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('FL', 'Florida'), ('GA', 'Georgia'),
        ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'),
        ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'), ('MO', 'Missouri'),
        ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'),
        ('NM', 'New Mexico'), ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'),
        ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'),
        ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'), ('WIS', 'Wisconsin'), ('WY', 'Wyoming'),
        ('DC', 'District of Columbia'),
        # Non-US Nations
        ('DE', 'Germany'),
        ('UK', 'United Kingdom'),
        ('WI', 'West Indies'),
    ]
    name_of_library_collection = models.CharField(max_length=500, null=True, blank=True)
    us_state_or_non_us_nation = models.CharField(max_length=10, choices=LOCATION_CHOICES, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    def __str__(self):
        return self.name_of_library_collection or "Unknown Location" 
    

class ProvenanceRecord(models.Model):
    copy = models.ForeignKey('Copy', on_delete=models.CASCADE, related_name='provenance_records')
    provenance_name = models.ForeignKey('ProvenanceName', on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.provenance_name} for {self.copy}"

class ProvenanceName(models.Model):
    EIGHTEENTH = '18'
    NINETEENTH = '19'
    TWENTIETH = '20'
    CENTURY_CHOICES = [
        (EIGHTEENTH, '18th-Cenutry'),
        (NINETEENTH, '19th-Century'),
        (TWENTIETH, 'Post-1900')
    ]
    MALE = 'M'
    FEMALE = 'F'
    UNKNOWN = 'U'
    NOT_APPLICABLE = 'X'
    GENDER_CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (UNKNOWN, 'Unknown'),
        (NOT_APPLICABLE, 'N/A'),
    ]
    name = models.CharField(max_length=256, null=True, blank=True)
    bio = models.CharField(max_length=1024, null=True, blank=True)
    viaf = models.CharField(max_length=256, null=True, blank=True)
    start_century = models.CharField(max_length=2, choices=CENTURY_CHOICES, null=True, blank=True)
    end_century = models.CharField(max_length=2, choices=CENTURY_CHOICES, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Provenance Names"
        verbose_name = "Provenance Name"


class Title(models.Model):
    title = models.CharField(max_length=128, unique=True)
    notes = models.TextField(null=True, blank=True, default='')
    image = models.ImageField(upload_to='titleicon', null=True, blank=True)

    def __str__(self):
        return self.title

class Edition(models.Model):
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    edition_number = models.CharField(max_length=20, unique=False, null=True, blank=True)
    edition_format = models.CharField(max_length=10, null=True, blank=True)
    notes = models.TextField(null=True, blank=True, default='')
    def __str__(self):
        return "%s %s" % (self.title, self.edition_number)

class Issue(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.CASCADE)
    year = models.CharField(max_length=20, default='')
    start_date = models.IntegerField(default=0)
    end_date = models.IntegerField(default=0)
    notes = models.TextField(null=True, blank=True)
    def __str__(self):
        return f"{self.edition} ({self.year})"

# Essential fields for all copies.
class Copy(models.Model):
    wc_number = models.CharField(max_length=50, unique=True)
    verification = models.CharField(max_length=1, choices=[('U', 'Unverified'), ('V', 'Verified'), ('F', 'False')], null=True, blank=True)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    shelfmark = models.CharField(max_length=500, null=True, blank=True)
    catalogue_url = models.URLField(max_length=500, null=True, blank=True)
    fragment = models.BooleanField(default=False)
    from_estc = models.BooleanField(default=False)
    digital_facsimile_url = models.URLField(max_length=500, null=True, blank=True)
    binding = models.CharField(max_length=500, null=True, blank=True)
    marginalia = models.TextField(null=True, blank=True)
    prov_info = models.TextField(null=True, blank=True)
    bibliography = models.TextField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    backend_notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    verified_by = models.CharField(max_length=500, null=True, blank=True)
    examined_by = models.CharField(max_length=500, null=True, blank=True)
    collated_by = models.CharField(max_length=500, null=True, blank=True)
    provenance = models.ForeignKey(ProvenanceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='copy_records')
    def __str__(self):
        return f"{self.wc_number} ({self.issue.year if self.issue else 'No Issue'})"


