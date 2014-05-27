from __future__ import print_function
from bs4 import BeautifulSoup
from collections import namedtuple
from dateutil.parser import parse as parsedate
from decimal import Decimal
import mechanize
import re


__all__ = ['Item', 'Account']
Item = namedtuple('Item', ['machine_readable',
                           'human_readable',
                           'due_date',
                           'times_renewed'])


class Account(object):
    """
    Account API wrapper to Sirsidynix sites.

    Since SirsiDynix will not give patron access to their products' APIs,
    this class pretends to be a web browser using the mechanize library.

    Account will log in when necessary. Information about the patron is
    accessible via Account.items() and Account.fines(). Renew materials
    using either Account.renew_all() or Account.renew().
    """

    def __init__(self, catalog, userid, password):
        """
        catalog  -- Library catalog URL complete with a scheme (HTTP/HTTPS)
        userid   -- Patron card number
        password -- Patron's PIN
        """
        self.catalog = catalog
        self.userid = userid
        self.password = password
        self._browser = mechanize.Browser()
        self._browser.set_handle_robots(False)

    def login(self):
        """Log user in."""
        self._get_homepage()
        self._browser.select_form(name='loginform')
        self._browser['user_id'] = self.userid
        self._browser['password'] = self.password
        self._browser.submit()
        if not self.logged_in:
            raise ValueError('Failed to log in. Invalid credentials?')

    def logout(self):
        """Log off user."""
        self._get_homepage()
        self._browser.follow_link(text='Logout')

    @property
    def logged_in(self):
        """Determines if user is logged in."""
        response = self._browser.response()
        if response is None:
            return False
        return bool(re.search(r'Welcome, \w+', response.read()))

    def items(self):
        """Get list of all checked out materials."""
        self._get_renew_my_materials()
        soup = self._soup()

        def is_item(tag):
            if tag.name != 'tr':
                return False
            regex = re.compile('itemlisting2?')
            return bool(tag.find(class_=regex, recursive=False))

        items = soup.find_all(is_item)
        return_items = []
        for item in items:
            machine_readable_name = item.find('input')['name']
            human_readable_name = item.find('label').text.strip() \
                .replace(u'\xa0\xa0\n\t\t \n          \n          ', ' -- ')
            due_date, times_renewed = [i.text.strip() for i in item
                                       .find_all('strong', limit=2)]
            try:
                times_renewed = int(times_renewed)
            except ValueError:  # Entry is an ILL, times_renewed == ''
                times_renewed = 0
            return_items.append(Item(
                machine_readable_name,
                human_readable_name,
                parsedate(due_date),
                times_renewed
            ))
        return return_items

    def renew(self, items):
        """Renew a list of items. Each item should be an instance of Item."""
        self._get_renew_my_materials()
        self._browser.select_form(name='renewitems')
        ids = [i.machine_readable for i in items]
        for id_ in ids:
            self._browser.find_control(id_).items[0].selected = True
        self._browser.submit()
        return self._renewal_status()

    def renew_all(self):
        """Blindly renew all items."""
        self._get_renew_my_materials()
        self._browser.select_form(name='renewitems')
        self._browser.form.set_value(['all'], name='selection_type')
        self._browser.submit()
        return self._renewal_status()

    def fines(self):
        """Get fines for logged in user as Decimal."""
        self._get_account_summary()
        soup = self._soup()

        li = soup.find('li', class_='summary').ul.li
        text = li.text.strip().replace('You owe', '')
        fines = Decimal(text.strip('$'))
        return fines

    def _get_homepage(self):
        return self._browser.open(self.catalog)

    def _get_my_account(self):
        if not self.logged_in:
            self.login()
        return self._browser.follow_link(text='My Account')

    def _get_renew_my_materials(self):
        self._get_my_account()
        return self._browser.follow_link(text='Renew My Materials')

    def _get_review_my_account(self):
        self._get_my_account()
        return self._browser.follow_link(text='Review My Account')

    def _get_account_summary(self):
        self._get_review_my_account()
        return self._browser.follow_link(text='Account Summary')

    def _renewal_status(self):
        return self._soup().h3.text.strip()

    def _soup(self):
        """Make a BeautifulSoup for the last response."""
        response = self._browser.response()
        return BeautifulSoup(response.read())

    def __repr__(self):
        return '<{}.{} {} {}>'.format(
            __name__,
            self.__class__.__name__,
            self.catalog,
            self.userid,
        )
