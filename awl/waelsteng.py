from django.contrib import admin
from django.contrib.admin.utils import lookup_field
from django.contrib.auth.models import User

from six.moves.html_parser import HTMLParser

# ============================================================================

class FakeRequest(object):
    pass


class AnchorParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        self.href = ''
        for attr in attrs:
            if attr[0] == 'href':
                self.href = attr[1]
                break

# ============================================================================

class AdminToolsMixin(object):
    """This mixin is used to help test django admin objects using the django
    client interface.  A superuser is created during setup which can then be
    used throughout.  

    .. note::

        :class:`AdminToolsMixin.initiate` must be called in the inheritor's
        :class:`TestCase.setUp` method to properly initialize.

    Once :class:`AdminToolsMixin.intiate` is called, the following will be
    available:

    :param site:
        An instance of an ``AdminSite`` to test against
    :param admin_user:
        A User object with staff and superuser privileges
    """
    #: Admin account's username during the tests
    USERNAME = 'admin'
    #: Admin account's password during the tests
    PASSWORD = 'admin'
    #: Admin account's email during the tests
    EMAIL = 'admin@admin.com'

    def initiate(self):
        """Sets up the :class:`AdminSite` and creates a user with the
        appropriate privileges.  This should be called from the inheritor's
        :class:`TestCase.setUp` method.
        """
        self.site = admin.sites.AdminSite()
        self.admin_user = User.objects.create_user(self.USERNAME, self.EMAIL,
            self.PASSWORD)
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.authed = False

    def authorize(self):
        """Authenticates the superuser account via the web login."""
        response = self.client.login(username=self.USERNAME, 
            password=self.PASSWORD)
        self.assertTrue(response)
        self.authed = True

    def authed_get(self, url, response_code=200, headers={}):
        """Does a django test client ``get`` against the given url after
        logging in the admin first.

        :param url:
            URL to fetch
        :param response_code:
            Expected response code from the URL fetch.  This value is
            asserted.  Defaults to 200
        :param headers:
            Optional dictionary of headers to send in the request
        :returns:
            Django testing ``Response`` object
        """
        if not self.authed:
            self.authorize()

        response = self.client.get(url, **headers)
        self.assertEqual(response_code, response.status_code)
        return response

    def authed_post(self, url, data, response_code=200, follow=False,
            headers={}):
        """Does a django test client ``post`` against the given url after
        logging in the admin first.

        :param url:
            URL to fetch
        :param data:
            Dictionary to form contents to post
        :param response_code:
            Expected response code from the URL fetch.  This value is
            asserted.  Defaults to 200
        :param headers:
            Optional dictionary of headers to send in with the request
        :returns:
            Django testing ``Response`` object
        """
        if not self.authed:
            self.authorize()

        response = self.client.post(url, data, follow=follow, **headers)
        self.assertEqual(response_code, response.status_code)
        return response

    def visit_admin_link(self, admin_model, instance, field_name,
            response_code=200, headers={}):
        """This method is used for testing links that are in the change list
        view of the django admin.  For the given instance and field name, the
        HTML link tags in the column are parsed for a URL and then invoked
        with :class:`AdminToolsMixin.authed_get`.

        :param admin_model:
            Instance of a :class:`admin.ModelAdmin` object that is responsible
            for displaying the change list
        :param instance:
            Object instance that is the row in the admin change list
        :param field_name:
            Name of the field/column to containing the HTML link to get a URL
            from to visit
        :param response_code:
            Expected HTTP status code resulting from the call.  The value of
            this is asserted.  Defaults to 200.
        :param headers:
            Optional dictionary of headers to send in the request
        :returns:
            Django test ``Response`` object
        :raises AttributeError:
            If the column does not contain a URL that can be parsed
        """
        html = self.field_value(admin_model, instance, field_name)
        try:
            parser = AnchorParser()
            parser.feed(html)
            url = parser.href
            if not url:
                raise AttributeError()
        except:
            raise AttributeError('href could not be parsed from *%s*' % html)

        return self.authed_get(url, response_code=response_code,
            headers=headers)

    def field_value(self, admin_model, instance, field_name):
        """Returns the value displayed in the column on the web interface for
        a given instance.

        :param admin_model:
            Instance of a :class:`admin.ModelAdmin` object that is responsible
            for displaying the change list
        :param instance:
            Object instance that is the row in the admin change list
        :field_name:
            Name of the field/column to fetch
        """
        _, _, value = lookup_field(field_name, instance, admin_model)
        return value

    def field_names(self, admin_model):
        """Returns the names of the fields/columns used by the given admin
        model.

        :param admin_model:
            Instance of a :class:`admin.ModelAdmin` object that is responsible
            for displaying the change list
        :returns:
            List of field names
        """
        request = FakeRequest()
        request.user = self.admin_user
        return admin_model.get_list_display(request)