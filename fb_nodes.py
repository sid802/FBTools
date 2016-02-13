#-*- encoding: utf-8 -*-
__author__ = 'Sid'

class FBNode(object):
    def __init__(self, fid):
        self.fid = fid

class FBUser(FBNode):
    def __init__(self, fid, full_name, user_name=None, friends=None, current_city=None, home_town=None, phones=None,
                 address=None, emails=None, birth_date=None, birth_year=None, gender=None, interested_in=None,
                 languages=None, family_members=None):
        self.fid = fid
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


