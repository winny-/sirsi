from __future__ import print_function
from bs4 import BeautifulSoup
import dateutil.parser
from decimal import Decimal
import mechanize
import re


__all__ = ['Item', 'Account']


class Item(object):
    """
    Library item retrieved from SirsiDynix's website.

    Due to the nature of how the website handles the unique identification
    for materials when renewing, canceling holds, or otherwise referencing
    a material, one must construct a token for the specific use case. See
    renew_token and hold_token for examples of how these tokens are
    constructed.

    token     -- machine readable token as obtained from <input[name]>.
    name      -- human readable name as obtained from <label>, is only
                 for show. Defaults to None.
    due_date  -- Due date; should be a Date object. Defaults to None.
    times_renewed -- number of successful renewals for the item Defaults to None.
    ill       -- Is the item an Inter-Library Loan? Defaults to None.
    renewable -- Can the item be renewed? Defaults to None.
    """

    RENEW_PREFIX = 'RENEW^'
    HOLD_PREFIX = 'HLD^TITLE^'
    TOKEN_PREFIX = re.compile(r'^({}|{})'.format(
        re.escape(RENEW_PREFIX),
        re.escape(HOLD_PREFIX),
    ))

    def __init__(self, token, name=None, due_date=None, times_renewed=None, ill=None, renewable=None):
        self.token = self.TOKEN_PREFIX.sub('', token)
        self.name = name
        self.due_date = due_date
        self.times_renewed = times_renewed
        self.ill = ill
        self.renewable = renewable

    @property
    def renew_token(self):
        return '{}{}'.format(self.RENEW_PREFIX, self.token)

    @property
    def hold_token(self):
        return '{}{}'.format(self.HOLD_PREFIX, self.token)

    def __str__(self):
        return '{}{}{}'.format(
            'ILL ' if self.ill else '',
            self.name,
            ', due {}'.format(self.due_date) if self.due_date is not None else '',
        )

    def __repr__(self):
        return '<{}.{} "{}" {}>'.format(
            __name__,
            self.__class__.__name__,
            self.token,
            self.due_date,
        )


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
            token = item.find('input')['name']
            name = item.find('label').text.strip().replace(
                u'\xa0\xa0\n\t\t \n          \n          ',
                ' -- '
            )
            due_date, times_renewed = [i.text.strip() for i in item
                                       .find_all('strong', limit=2)]
            due_date = dateutil.parser.parse(due_date)
            try:
                times_renewed = int(times_renewed)
            except ValueError:  # Entry is an ILL, times_renewed == ''
                times_renewed = 0
            return_items.append(Item(
                token,
                name,
                due_date,
                times_renewed
            ))
        return return_items

    def renew(self, items):
        """Renew a list of items. Each item should be an instance of Item."""
        self._get_renew_my_materials()
        self._browser.select_form(name='renewitems')
        for renew_token in [i.renew_token for i in items]:
            self._browser.find_control(renew_token).items[0].selected = True
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
