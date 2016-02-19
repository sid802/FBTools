#-*- encoding: utf-8 -*-
__author__ = 'Sid'

class FBNode(object):
    def __init__(self, fid):
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
    def __init__(self, fid, full_name, user_name=None, friends=None, current_city=None, home_town=None, phones=None,
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
    def __init__(self, fid, author=None, taggees=None, likers=None, commenters=None, comments=None, sharers=None, privacy=None):
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

        info_match = self._regexes[regex_name].search(src_string)
        if info_match is None:
            return None
        return info_match.group('result')