from __future__ import print_function
from bs4 import BeautifulSoup
from collections import namedtuple
from dateutil.parser import parse as parsedate
from decimal import Decimal
import mechanize
import re


Item = namedtuple('Item', ['machine_readable', 'human_readable', 'due_date', 'times_renewed'])


class Account(object):

    def __init__(self, catalog, userid, password):
        self.catalog = catalog
        self.userid = userid
        self.password = password
        self._browser = mechanize.Browser()
        self._browser.set_handle_robots(False)

    def _get_homepage(self):
        return self._browser.open(self.catalog)

    def login(self):
        """Log user in."""
        self._get_homepage()
        self._browser.select_form(name='loginform')
        self._browser['user_id'] = self.userid
        self._browser['password'] = self.password
        self._browser.submit()
        if not self.logged_in():
            raise ValueError('Failed to log in. Invalid credentials?')

    def logged_in(self):
        """Determines if user is logged in."""
        response = self._browser.response()
        if response is None:
            return False
        return bool(re.search(r'Welcome, \w+', response.read()))

    def logout(self):
        """Log off user."""
        self._get_homepage()
        self._browser.follow_link(text='Logout')

    def _get_my_account(self):
        if not self.logged_in():
            self.login()
        return self._browser.follow_link(text='My Account')

    def _get_renew_my_materials(self):
        self._get_my_account()
        return self._browser.follow_link(text='Renew My Materials')

    def renew_all(self):
        """Blindly renew all items."""
        self._get_renew_my_materials()
        self._browser.select_form(name='renewitems')
        self._browser.form.set_value(['all'], name='selection_type')
        self._browser.submit()
        return self._renewal_status()

    def renew(self, items):
        """Renew a list of items. Each item should be an instance of Item."""
        self._get_renew_my_materials()
        self._browser.select_form(name='renewitems')
        ids = [i.machine_readable for i in items]
        for id_ in ids:
            self._browser.find_control(id_).items[0].selected = True
        self._browser.submit()
        return self._renewal_status()

    def _renewal_status(self):
        return self._soup().h3.text.strip()

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
            due_date, times_renewed = [i.text.strip() for i in item.find_all('strong', limit=2)]
            return_items.append(Item(
                machine_readable_name,
                human_readable_name,
                parsedate(due_date),
                int(times_renewed)
                ))
        return return_items

    def _get_review_my_account(self):
        self._get_my_account()
        return self._browser.follow_link(text='Review My Account')

    def _get_account_summary(self):
        self._get_review_my_account()
        return self._browser.follow_link(text='Account Summary')

    def _soup(self):
        """Make a BeautifulSoup for the last response."""
        response = self._browser.response()
        return BeautifulSoup(response.read())

    def fines(self):
        """Get fines for logged in user as Decimal."""
        self._get_account_summary()
        soup = self._soup()

        li = soup.find('li', class_='summary').ul.li
        text = li.text.strip().replace('You owe', '')
        fines = Decimal(text.strip('$'))
        return fines
