# wheatleycensus/tests.py
# Contains unit tests for the Wheatley Census app.
# Includes setup for test data and test cases for search and filtering functionality.

from django.test import TestCase
from django.urls import reverse
from .models import Copy, Location, ProvenanceName, Title, Edition, Issue

class SearchViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1) Create a title (this is the missing step)
        title = Title.objects.create(title="Test Play", author="Tester")

        # 2) Create an edition pointing at that Title
        ed = Edition.objects.create(
            title=title,
            edition_number="1",        # or whatever your field is
            author="Tester"            # if you have an author field here
        )

        # 3) Create an issue on that edition
        iss = Issue.objects.create(
            edition=ed,
            year=1600,
            start_date=1600,
            end_date=1600,
            stc_wing="Wing123"
        )

        # 4) Create a location
        loc = Location.objects.create(name_of_library_collection="Oxford Library")

        # 5) Create a copy on that issue & location
        copy = Copy.objects.create(
            issue=iss,
            location=loc,
            wc_number="123.4",
            verification='V'
        )

        # 6) Link a provenance record
        prov = ProvenanceName.objects.create(name="Smith", gender="F")
        copy.provenance_records.create(provenance_name=prov)

    def assertCount(self, url, expected):
        resp = self.client.get(url)
        self.assertContains(resp, 'class="play-detail-set"')
        self.assertIn(f"Extant copies: {expected}", resp.content.decode())

    def test_location_filter(self):
        self.assertCount(
            reverse('search') + '?field=location&value=Oxford',
            expected=1
        )

    def test_keyword_filter(self):
        self.assertCount(
            reverse('search') + '?field=keyword&value=Test',
            expected=1
        )

    def test_provenance_name(self):
        self.assertCount(
            reverse('search') + '?field=provenance_name&value=Smith',
            expected=1
        )

    def test_gender_filter(self):
        self.assertCount(
            reverse('search') + '?field=gender&value=Female',
            expected=1
        )

    def test_census_id(self):
        self.assertCount(
            reverse('search') + '?field=census_id&value=123.4',
            expected=1
        )
