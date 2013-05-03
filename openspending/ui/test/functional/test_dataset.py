import csv
import json
from StringIO import StringIO

from .. import ControllerTestCase, url, helpers as h
from openspending.model import Dataset, meta as db


class TestDatasetController(ControllerTestCase):

    def setup(self):

        super(TestDatasetController, self).setup()
        self.dataset = h.load_fixture('cra')
        self.user = h.make_account('test')
        h.clean_and_reindex_solr()

    def test_index(self):
        response = self.app.get(url(controller='dataset', action='index'))
        assert 'The database contains the following datasets' in response
        assert 'cra' in response

    def test_index_json(self):
        response = self.app.get(url(controller='dataset', action='index', format='json'))
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 1)
        h.assert_equal(obj['datasets'][0]['name'], 'cra')
        h.assert_equal(obj['datasets'][0]['label'], 'Country Regional Analysis v2009')

    def test_index_category(self):
        """
        Test filtering of datasets by providing a category url parameter.

        This does four different tests. We try to get all of the
        different categories OpenSpending provides and then try to fetch
        with a non-existent category name.

        This test case uses json by default since it's more likely to be
        useful there instead of on the html presentation of the site which
        isn't linked anywhere
        """

        # Set the category of cra to 'spending'
        cra = Dataset.by_name('cra')
        cra.category = 'spending'
        db.session.commit()

        # Test if budget category returns anything (shouldn't return one)
        response = self.app.get(url(controller='dataset', action='index', format='json'), params={'category':'budget'})
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 0)
        
        # Test if spending category returns anything (it should return cra)
        response = self.app.get(url(controller='dataset', action='index', format='json'), params={'category':'spending'})
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 1)
        h.assert_equal(obj['datasets'][0]['name'], 'cra')
        h.assert_equal(obj['datasets'][0]['label'], 'Country Regional Analysis v2009')

        # Test if other category returns anything (shouldn't return one)
        response = self.app.get(url(controller='dataset', action='index', format='json'), params={'category':'other'})
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 0)

        # Test if random category name returns anything (shouldn't return one)
        response = self.app.get(url(controller='dataset', action='index', format='json'), params={'category':'random-non-existent-category'})
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 0)

    def test_index_hide_private(self):
        cra = Dataset.by_name('cra')
        cra.private = True
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='index', format='json'))
        obj = json.loads(response.body)
        h.assert_equal(len(obj['datasets']), 0)

    def test_index_csv(self):
        response = self.app.get(url(controller='dataset', action='index', format='csv'))
        r = csv.DictReader(StringIO(response.body))
        obj = [l for l in r]
        h.assert_equal(len(obj), 1)
        h.assert_equal(obj[0]['name'], 'cra')
        h.assert_equal(obj[0]['label'], 'Country Regional Analysis v2009')

    def test_view(self):
        response = self.app.get(url(controller='dataset', action='view', dataset='cra'))
        h.assert_true('Country Regional Analysis v2009' in response,
                      "'Country Regional Analysis v2009' not in response!")
        #h.assert_true('openspending_browser' in response, "'openspending_browser' not in response!")

    def test_view_private(self):
        cra = Dataset.by_name('cra')
        cra.private = True
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='view',
            dataset='cra'), status=403)
        h.assert_false('Country Regional Analysis v2009' in response,
                      "'Country Regional Analysis v2009' not in response!")
        h.assert_false('openspending_browser' in response, "'openspending_browser' not in response!")

    def test_about_has_format_links(self):
        url_ = url(controller='dataset', action='about', dataset='cra')
        response = self.app.get(url_)

        url_ = url(controller='dataset', action='model', dataset='cra',
           format='json')

        h.assert_true(url_ in response,
                      "Link to view page (JSON format) not in response!")

    def test_about_has_profile_links(self):
        self.dataset.managers.append(self.user)
        db.session.add(self.dataset)
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='about',
                                dataset='cra'))
        assert ('<li><a href="/account/profile/test">Test User</a></li>' in
                response.body)

    def test_view_json(self):
        response = self.app.get(url(controller='dataset', action='view',
                                    dataset='cra', format='json'))
        obj = json.loads(response.body)
        h.assert_equal(obj['name'], 'cra')
        h.assert_equal(obj['label'], 'Country Regional Analysis v2009')

    def test_model_json(self):
        response = self.app.get(url(controller='dataset', action='model',
                                    dataset='cra', format='json'))
        obj = json.loads(response.body)
        assert 'dataset' in obj.keys(), obj
        h.assert_equal(obj['dataset']['name'], 'cra')
        h.assert_equal(obj['dataset']['label'], 'Country Regional Analysis v2009')

    def test_entries(self):
        self.app.get(url(controller='entry', action='index', dataset='cra'))

    def test_entries_json_export(self):
        response = self.app.get(url(controller='entry',
                                    action='index',
                                    dataset='cra',
                                    format='json'))
        assert '/api/2/search' in response.headers['Location'], response.headers
        assert 'format=json' in response.headers['Location'], response.headers

    def test_entries_csv_export(self):
        response = self.app.get(url(controller='entry',
                                    action='index',
                                    dataset='cra',
                                    format='csv'))
        assert '/api/2/search' in response.headers['Location'], response.headers
        assert 'format=csv' in response.headers['Location'], response.headers
        response = response.follow()
        r = csv.DictReader(StringIO(response.body))
        obj = [l for l in r]
        h.assert_equal(len(obj), 36)

    def test_new_form(self):
        response = self.app.get(url(controller='dataset', action='new'),
            params={'limit': '20'}, extra_environ={'REMOTE_USER': 'test'})
        assert "Import a dataset" in response.body

    def test_create_dataset(self):
        response = self.app.post(url(controller='dataset', action='create'),
            extra_environ={'REMOTE_USER': 'test'})
        assert "Import a dataset" in response.body
        assert "Required" in response.body

        params = {'name': 'testds', 'label': 'Test Dataset',
                  'category': 'budget', 'description': 'I\'m a banana!',
                  'currency': 'EUR'}

        response = self.app.post(url(controller='dataset', action='create'),
                params=params, extra_environ={'REMOTE_USER': 'test'})
        assert "302" in response.status

        ds = Dataset.by_name('testds')
        assert ds.label == params['label'], ds

    def test_feeds(self):
        # Anonymous user with one public dataset
        response = self.app.get(url(controller='dataset', action='feed_rss'),
                                expect_errors=True)
        assert 'application/xml' in response.content_type
        assert '<title>Recently Created Datasets</title>' in response
        assert '<item><title>Country Regional Analysis v2009' in response
        cra = Dataset.by_name('cra')
        cra.private = True
        db.session.add(cra)
        db.session.commit()

        # Anonymous user with one private dataset
        response = self.app.get(url(controller='dataset', action='feed_rss'),
                                expect_errors=True)
        assert 'application/xml' in response.content_type
        assert '<title>Recently Created Datasets</title>' in response
        assert '<item><title>Country Regional Analysis v2009' not in response

        # Logged in user with one public dataset
        cra.private = False
        db.session.add(cra)
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='feed_rss'),
                                expect_errors=True,
                                extra_environ={'REMOTE_USER': 'test'})
        assert 'application/xml' in response.content_type
        assert '<title>Recently Created Datasets</title>' in response
        assert '<item><title>Country Regional Analysis v2009' in response

        # Logged in user with one private dataset
        cra.private = True
        db.session.add(cra)
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='feed_rss'),
                                expect_errors=True,
                                extra_environ={'REMOTE_USER': 'test'})
        assert 'application/xml' in response.content_type
        assert '<title>Recently Created Datasets</title>' in response
        assert '<item><title>Country Regional Analysis v2009' not in response

        # Logged in admin user with one private dataset
        admin_user = h.make_account('admin')
        admin_user.admin = True
        db.session.add(admin_user)
        db.session.commit()
        response = self.app.get(url(controller='dataset', action='feed_rss'),
            extra_environ={'REMOTE_USER': 'admin'})
        assert '<title>Recently Created Datasets</title>' in response
        assert '<item><title>Country Regional Analysis v2009' in response
        assert 'application/xml' in response.content_type

        response = self.app.get(url(controller='dataset', action='index'))
        assert ('<link rel="alternate" type="application/rss+xml" title="'
            'Latest Datasets on OpenSpending" href="/datasets.rss"' in
            response)
