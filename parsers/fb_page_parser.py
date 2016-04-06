__author__ = 'Sid'

from lxml import html
from parsers import fb_constants as constants
from fb_main import *
from fb_main import _default_vs_new
from fb_df import *
import re
from datetime import datetime

class PageParser(FBParser):
    """
    Class to parse Page metadata
    """
    def __init__(self, pages_ids=None, parse_likers=True):
        """
        :param pages_ids: (list), Pages Id's
        :param parse_likers: (boolean), whether to parse the users
        :return:
        """
        super(PageParser, self).__init__()
        self.pages_ids = pages_ids
        self.parse_likers = parse_likers

    @FBParser.browser_needed
    def parse_page(self, page_id, extract_likers=False):
        """
        :param page_id: (string), page id
        :return: FBPage instance
        """

        BASE_URL = 'https://facebook.com/{fid}/{tab}'
        self.driver.get(BASE_URL.format(fid=page_id,
                                        tab='')
                        )

        page = FBPage(page_id)

        # Page's username
        match = constants.FBRegexes.url_user.search(self.driver.current_url)
        if match:
            page.page_user = match.group('result')

        tree = html.fromstring(self.driver.page_source)

        # Page's title
        match = tree.xpath(constants.FBXpaths.page_title)
        if len(match) > 0:
            page.page_title = match[0]

        # Page's likers amount
        match = tree.xpath(constants.FBXpaths.page_likers_amount)
        if len(match) == 0:
            # Try second xpath
            match = tree.xpath(constants.FBXpaths.page_likers_amount_secondary)

        if len(match) > 0:
            likers_amount_string = match[0]
            likers_amount_digits = re.sub(r'\D', '', likers_amount_string)  # example: '8,475 people liked this' -> '8475'
            page.likers_amount = int(likers_amount_digits)

        self.driver.get(BASE_URL.format(fid=page_id,
                                        tab='info')
                        )
        tree = html.fromstring(self.driver.page_source)

        # Page's short description
        match = tree.xpath(constants.FBXpaths.page_short_desc)
        if len(match) > 0:
            page.short_description = ''.join(match)

        # Page's long description
        match = tree.xpath(constants.FBXpaths.page_desc_is_split)
        if len(match) > 0:
            # Long description is split
            long_desc_list = tree.xpath(constants.FBXpaths.page_long_desc_split)  # Returns list of text
        else:
            long_desc_list = tree.xpath(constants.FBXpaths.page_long_desc_unified)  # Returns list of text

        if len(long_desc_list) > 0:
            page.long_description = ''.join(long_desc_list)

        return page

    @FBParser.browser_needed
    def run(self, email, password, parse_likers=None):
        """
        :param email: Email to connect with
        :param password: Password to connect with
        :param parse_likers: (boolean), defaults to when the parser was created
        :return: List of pages metadata
        """

        user_id = self.init_connect(email, password)

        parse_likers = _default_vs_new(self.parse_likers, parse_likers)

        all_pages = FBPageList()

        for page_id in self.pages_ids:
            page = self.parse_page(page_id, parse_likers)
            all_pages.append(page)

        return all_pages

parser = PageParser(['65879791704', '843603385676595'], False)
pages = parser.run('XXXXXX', 'YYYYY')
for page in pages:
    print
    for attr, val in page.__dict__.iteritems():
        print "{0}: {1}".format(attr, val)
