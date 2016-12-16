#-*- encoding: utf-8 -*-
__author__ = 'Sid'
from HTMLParser import HTMLParser
import json

from selenium import webdriver
from datetime import datetime
from parsers import fb_constants as constants


class FBNode(object):
    def __init__(self, fid=None):
        self.fid = fid

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'FID: {0}'.format(unicode(self.fid))
    def __hash__(self):
        return hash(self.fid)
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

    def import_to_db(self, cursor):
        """
        :param cursor: cursor to DB
        Imports some fields to a DB
        """

        USER_INSERT = r"INSERT INTO USERS(ID, USER_NAME, FULL_NAME) " \
                          r"VALUES(%(id)s, %(username)s, %(fullname)s) " \
                          r"ON DUPLICATE KEY UPDATE USER_NAME=%(username)s, FULL_NAME=%(fullname)s"

        cursor.execute(USER_INSERT, {
            'id': self.fid, 'username': self.user_name, 'fullname': self.full_name
        })

    def __repr__(self):
        return self.__unicode__().encode('utf-8')

    def __unicode__(self):
        return u'FID: {0}, username: {1}, full name: {2}'.format(self.fid, self.user_name, self.full_name)

class FBPicture(FBNode):
    def __init__(self, fid=None, author=None, taggees=None, likers=None, published=None,
                 caption=None, commenters=None, comments=None, sharers=None, privacy=None):
        super(FBPicture, self).__init__(fid)
        self.author = author  # FBUser
        self.taggees = taggees  # List of FBUsers
        self.caption = caption
        self.commenters = commenters  # List of FBUsers
        self.likers = likers  # List of FBUsers
        self.sharers = sharers  # List of FBUsers
        self.privacy = privacy  # String
        self.comments = comments  # List of FBComments
        self.published = published  # datetime object

class FBPage(FBNode):
    def __init__(self, fid=None, page_user=None, page_title=None, likers=None, likers_amount=None,
                 short_description=None, long_description=None):
        super(FBPage, self).__init__(fid)
        self.page_user = page_user
        self.page_title = page_title
        self.likers = likers
        self.likers_amount = likers_amount
        self.short_description= short_description
        self.long_description = long_description

class FBGroup(FBNode):
    def __init__(self, fbid, username=None, title=None, privacy=None, description=None,
                 category=None, members_amount=None, members=None):
        super(FBGroup, self).__init__(fbid)
        self.username = username  # username (string)
        self.title = title  # full name (string)
        self.privacy = privacy  # string
        self.description = description  # string
        self.members_amount = members_amount  # int
        self.members = members  # list of FBUsers
        self.category = category  # Category (string)

    def import_to_db(self, parse_time, cursor):
        """
        :param parse_time: The time the metadata has been parsed
        :param cursor: cursor to DB
        imports some fields to DB
        """

        GROUP_INSERT = r"INSERT INTO GROUPS(ID, NAME_R, USERNAME, DESCRIPTION, CATEGORY, PRIVACY, MEMBERS_AMOUNT, " \
                       r"LAST_META_PARSE) " \
                       r"VALUES(%(id)s, %(name)s, %(user)s, %(desc)s, %(cat)s, %(priv)s, %(members)s, %(time)s )" \
                       r"ON DUPLICATE KEY " \
                       r"UPDATE NAME_R=%(name)s, USERNAME=%(user)s, DESCRIPTION=%(desc)s, CATEGORY=%(cat)s," \
                       r"PRIVACY=%(priv)s, MEMBERS_AMOUNT=%(members)s, LAST_META_PARSE=%(time)s"

        cursor.execute(GROUP_INSERT, {
            'id': self.fid, 'name': self.title, 'user': self.username, 'desc': self.description,
            'cat': self.category, 'priv': self.privacy, 'members': self.members_amount, 'time': parse_time
        })

class FBPost(FBNode):
    """
    class to contain post about a post
    """

    def __init__(self, id='', group=None, author=None, date_time='', content='', commenters=None):
        super(FBPost, self).__init__(id)
        self.group = group
        self.author = author

        if commenters:
            self.comments = commenters
        else:
            self.comments = []

        self.content = content

        if type(date_time) == int:
            # timestamp unix
            post_datetime = datetime.fromtimestamp(date_time)
        elif type(date_time) == datetime:
            post_datetime = date_time
        else:
            post_datetime = None

        self.date_time = post_datetime

class FBParser(object):
    """
    General FB Parser
    """

    def __init__(self, debug=False):
        self.driver = None  # Will be initialized later
        self._html_parser = HTMLParser()
        self._user_id = None  # Will be initialized later
        self.debug = debug

    def set_driver(self, driver):
        self.driver = driver

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

    def _parse_payload_from_ajax_response(self, ajax_response, source=None):
        """
        :param ajax_response: full response
        :param source: what do we parse (page/friends etc)
        :return: string of actual html response
        """
        if self.debug:
            print 'full response:', ajax_response
        full_json_match = constants.FBRegexes.json_from_html.search(ajax_response)  # Keep only json string
        if not full_json_match:
            return None

        full_json = full_json_match.group('json')
        if self.debug:
            print 'json:', full_json
        try:
            json_dict = json.loads(full_json)
        except Exception, e:
            print 'Could not load json'
            return None

        try:
            if source in ['friends', 'group_posts']:
                return json_dict['payload']
            elif source in ['group', 'mutual_friends']:
                return json_dict['domops'][0][3]['__html']
            elif source == 'group':
                return json_dict
            return json_dict['jsmods']['markup'][0][1]['__html']
        except Exception:
            try:
                error = json['jsmods']['require'][1][3][0]['__html']
            except Exception:
                error = 'Couldnt parse from picture'
            raise JSONParseError(error)
            return None

    def run(self):
        raise NotImplementedError("You must implement this method")

    def run_already_connected(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    @staticmethod
    def browser_needed(func):
        def func_wrapper(self, *args, **kwargs):
            if self.driver is None:
                self.driver = webdriver.Chrome()
            return func(self, *args, **kwargs)
        return func_wrapper

class JSONParseError(Exception):
    def __init__(self, message):
        super(JSONParseError, self).__init__(message)

def _default_vs_new(default_val, new_val):
    """
    :param default_val: Default value
    :param new_val: New Value
    :return: new_val if not null, default otherwise
    """
    if new_val is not None:
        return new_val
    return default_val

def _stronger_value(original_value, new_value):
    """
    :param original_value: original value
    :param new_value: value to replace the original value
    :return: new_value if it isnt null, original_value otherwise
    """
    if new_value:
        return new_value
    return original_value

def blankify(str_txt, wanted_type=unicode):
    """
    :param str_txt: Original text
    :return: Blank string if str_txt is None
    """
    if str_txt is None:
        return wanted_type('')
    return str_txt