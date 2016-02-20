#-*- encoding: utf-8 -*-
__author__ = 'Sid'
from HTMLParser import HTMLParser
import json

from selenium import webdriver

from parsers import fb_constants as constants


class FBNode(object):
    def __init__(self, fid=None):
        self.fid = fid

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'FID: {0}'.format(unicode(self.fid))
    def __hash__(self):
        return self.fid
    def __eq__(self, other):
        if isinstance(other, FBNode) and self.fid == other.fid:
            return True
        return False

class FBUser(FBNode):
    def __init__(self, fid=None, full_name=None, user_name=None, friends=None, current_city=None, home_town=None, phones=None,
                 address=None, emails=None, birth_date=None, birth_year=None, gender=None, interested_in=None,
                 languages=None, family_members=None):
        super(FBUser, self).__init__(fid)
        self.full_name = full_name  # String
        self.user_name = user_name  # String
        self.friends = friends
        self.current_city = current_city  # String
        self.home_town = home_town  # String
        self.phones = phones  # String
        self.address = address  # String
        self.emails = emails  # String
        self.birth_date = birth_date  # String
        self.birth_year = birth_year  # String
        self.gender = gender  # String
        self.interested_in = interested_in  # String
        self.languages = languages  # List of string
        self.family_members = family_members  # List of FBUsers

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'FID: {0}, username: {1}, full name: {2}'.format(self.fid, self.user_name, self.full_name)

class FBPicture(FBNode):
    def __init__(self, fid=None, author=None, taggees=None, likers=None, commenters=None, comments=None, sharers=None, privacy=None):
        super(FBPicture, self).__init__(fid)
        self.author = author  # FBUser
        self.taggees = taggees  # List of FBUsers
        self.commenters = commenters  # List of FBUsers
        self.likers = likers  # List of FBUsers
        self.sharers = sharers  # List of FBUsers
        self.privacy = privacy  # String
        self.comments = comments  # List of FBComments


class FBParser(object):
    """
    General FB Parser
    """

    _html_parser = HTMLParser()
    driver = None  # Will be initialized later

    def init_connect(self, email, password):
        """
        Connect to facebook
        return user fid if successfull, None otherwise
        """
        self.driver.get('https://facebook.com')

        # set email
        email_element = self.driver.find_element_by_id('email')
        email_element.send_keys(email)

        # set password
        password_element = self.driver.find_element_by_id('pass')
        password_element.send_keys(password)

        # press login button
        self.driver.find_element_by_id('loginbutton').click()

        if 'attempt' in self.driver.current_url:
            # Failed to log in
            return None

        my_id_match = constants.FBRegexes.my_fid.search(self.driver.page_source)
        if my_id_match:
            return my_id_match.group('result')

        return None

    def _fix_payload(self, payload):
        """
        :param payload: html payload
        :return: unescaped html
        """

        payload_html = payload.replace(r'\u003C', '<')
        return self._html_parser.unescape(payload_html)

    def _info_from_url(self, regex_name, src_string):
        """
        :param regex: regex's name in dict. will be used to extract the info
        :param src_string: source string to extract regex from
        :return: extracted info, None if not found
        """
        info_match = getattr(constants.FBRegexes, regex_name).search(src_string)
        if info_match is None:
            return None
        return info_match.group('result')

    def _parse_user_from_link(self, user_link):
        """
        :param xpath_element: XPath element
        :return: FBUser instance of current element
        """
        username = full_name = fid = None

        fid_url = user_link.xpath(constants.FBXpaths.user_fid_url)
        if len(fid_url) > 0:
            fid = unicode(self._info_from_url('liker_fid_from_url', fid_url[0]))

        username_url = user_link.xpath(constants.FBXpaths.user_username_url)
        if len(username_url) > 0:
            username = unicode(self._info_from_url('liker_username_from_url', username_url[0]))
            if username in [u'profile.php', u'people']:
                username = None

        full_name_result = user_link.xpath(constants.FBXpaths.user_full_name)
        if len(full_name_result) > 0:
            full_name = unicode(full_name_result[0])

        return FBUser(fid, full_name, username)

    def quit(self):
        """
        :return: Close browser
        """
        self.driver.quit()
        self.driver = None

    def _parse_payload_from_ajax_response(self, ajax_response):
        """
        :param ajax_response: full response
        :return: string of actual html response
        """

        full_json_match = constants.FBRegexes.json_from_html.search(ajax_response)  # Keep only json string
        if not full_json_match:
            return None

        full_json = full_json_match.group()
        json_dict = json.loads(full_json)
        try:
            return json_dict['jsmods']['markup'][0][1]['__html']
        except Exception:
            return None

    @staticmethod
    def browser_needed(func):
        def func_wrapper(self, *args, **kwargs):
            if self.driver is None:
                self.driver = webdriver.Chrome()
            return func(self, *args, **kwargs)
        return func_wrapper