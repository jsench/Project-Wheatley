from django.db import models
from django.conf import settings

### Main Site Operations ###

class Location(models.Model):
    name = models.CharField(max_length=500)

    def __str__(self):
        return self.name

class StaticPageText(models.Model):
    content = models.TextField(null=True, blank=True, default=None)
    viewname = models.CharField(max_length=255, default='', null=True, blank=True)

    def __str__(self):
        return self.viewname
    class Meta:
        verbose_name_plural = "Static Pages"


### Core Data Tables ###

class ProvenanceName(models.Model):
    SEVENTEENTH = '17'
    EIGHTEENTH = '18'
    NINETEENTH = '19'
    TWENTIETH = '20'
    CENTURY_CHOICES = [
        (SEVENTEENTH, 'Pre-1700'),
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
    apocryphal = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True, default='')
    image = models.ImageField(upload_to='titleicon', null=True, blank=True)

    def __str__(self):
        return self.title

class Edition(models.Model):
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    Edition_number = models.CharField(max_length=20, unique=False, null=True, blank=True)
    Edition_format = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return "%s Edition %s" % (self.title, self.Edition_number)

class Issue(models.Model):
    edition = models.ForeignKey(Edition, unique=False, on_delete=models.CASCADE)
    STC_Wing = models.CharField(max_length=20)
    ESTC = models.CharField(max_length=20)
    year = models.CharField(max_length=20, default='')
    start_date = models.IntegerField(default=0)
    end_date = models.IntegerField(default=0)
    DEEP = models.CharField(max_length=20, default='', null=True, blank=True)
    notes = models.TextField(null=True, blank=True, default='')
    Variant_Description = models.TextField(null=True, blank=True, default='')

    def ESTC_as_list(self):
        estc_list = self.ESTC.split('; ')
        return [(estc, (i + 1) == len(estc_list))
                for i, estc in enumerate(estc_list)]

    def DEEP_as_list(self):
        deep_list = self.DEEP.split('; ')
        return [(deep, (i + 1) == len(deep_list))
                for i, deep in enumerate(deep_list)]

    def __str__(self):
        return "%s ESTC %s" % (self.edition, self.ESTC)

# Essential fields for all copies.
class Copy(models.Model):
    MC = models.CharField(max_length=40, default='', null=True, blank=True)
    UNVERIFIED = 'U'
    VERIFIED = 'V'
    FALSE = 'F'
    VERIFICATION_CHOICES = [
        (UNVERIFIED, 'Unverified'),
        (VERIFIED, 'Verified'),
        (FALSE, 'False'),
        ]
    verification = models.CharField(max_length=1, choices=VERIFICATION_CHOICES, default='Unverified')
    issue = models.ForeignKey(Issue, unique=False, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, unique=False, null=True, blank=True, on_delete=models.CASCADE)
    Shelfmark = models.CharField(max_length=500, default='', null=True, blank=True)
    Digital_Facsimile_URL = models.URLField(max_length=500, null=True, blank=True)
    Height = models.FloatField(default=0, null=True, blank=True)
    Width = models.FloatField(default=0, null=True, blank=True)
    Binding = models.CharField(max_length=500, default='', null=True, blank=True)
    in_early_sammelband = models.BooleanField(default=False)
    fragment = models.BooleanField(default=False)
    Marginalia = models.TextField(null=True, blank=True, default='')
    Local_Notes = models.TextField(null=True, blank=True, default='')
    prov_info = models.TextField(null=True, blank=True, default='')
    provenance_search_names = models.ManyToManyField(
        ProvenanceName,
        through='ProvenanceOwnership',
        through_fields=('copy', 'owner')
        )
    bibliography = models.TextField(null=True, blank=True, default='')
    from_estc = models.BooleanField(default=False)
    backend_notes = models.TextField(null=True, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="user_submitted_copies",
                               default=None, null=True, blank=True, on_delete=models.SET_NULL)
    verified_by = models.CharField(max_length=500, default='', null=True, blank=True)
    examined_by = models.CharField(max_length=500, default='', null=True, blank=True)
    collated_by = models.CharField(max_length=500, default='', null=True, blank=True)

    def __str__(self):
        return  "{} ({}), MC# {}".format(self.issue, self.issue.year, self.MC)
    class Meta:
        verbose_name_plural = "Copies"

class ProvenanceOwnership(models.Model):
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE)
    owner = models.ForeignKey(ProvenanceName, on_delete=models.CASCADE)

    def __str__(self):
        return '{} owned {}'.format(
            self.owner.name,
            self.copy
        )
    class Meta:
        verbose_name_plural = "Provenance Records"
        verbose_name = "Provenance Record"
