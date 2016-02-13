#-*- encoding: utf-8 -*-
__author__ = 'Sid'


##############################################
#
# Extract metadata from facebook Photos
#
# Extract anybody who posted/commented
# with the phone numbers/emails he posted
#
##############################################

import re, time, sys, json, export_to_file, canonization
from datetime import datetime
from base64 import b64encode
from HTMLParser import HTMLParser

from selenium import webdriver
from lxml import html

from mysql import connector
from fb_nodes import *

def _default_vs_new(default_val, new_val):
    """
    :param default_val: Default value
    :param new_val: New Value
    :return: new_val if not null, default otherwise
    """
    if new_val is not None:
        return new_val
    return default_val

class PhotoParser(object):
    """
    Class to parse photo's metada
    """
    def __init__(self, photos_fids, extract_taggees=True, extract_likers=True, extract_commenters=True,
                 extract_comments=True, extract_privacy=True):
        """
        :param photos_fids: List of picture fb_ids
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        """
        self.photos_fids = photos_fids
        self.extract_taggees = extract_taggees
        self.extract_likers = extract_likers
        self.extract_commenters = extract_commenters
        self.extract_comments = extract_comments
        self.extract_privacy = extract_privacy
        self.driver = None  # Will be initialized later

    def init_connect(self, email, password):
        """
        Connect to facebook
        return user fid if successfull, None otherwise
        """
        self.driver.get('https://facebook.com')

        # set email
        email_element = self.driver.find_element_by_id('email')
        email_element.send_keys(self.email)

        # set password
        password_element = self.driver.find_element_by_id('pass')
        password_element.send_keys(self.password)

        # press login button
        self.driver.find_element_by_id('loginbutton').click()

        if 'attempt' in self.driver.current_url:
            # Failed to log in
            return None

        my_id_match = self._regexes['my_id'].search(self.driver.page_source)
        if my_id_match:
            return my_id_match.group('result')

        return None

    def parse_photo(self, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True):
        """
        :param photo_html: Current photo HTML
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        :return: FBPhoto instance of current photo
        """
        # TODO: init xpaths if __init__ function
        pass

    def run(self, email, password, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True):

        user_fid = self.init_connect(email, password)
        if user_fid is None:
            raise Exception("Login to Facebook failed")

        return self.parse_all(user_fid, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True)

    def parse_all(self, user_id, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True):
        """
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        :return: List of FBPhoto instances
        """

        extract_taggees = _default_vs_new(self.extract_taggees, extract_taggees)
        extract_likers = _default_vs_new(self.extract_likers, extract_likers)
        extract_commenters = _default_vs_new(self.extract_commenters, extract_commenters)
        extract_comments = _default_vs_new(self.extract_comments, extract_comments)
        extract_privacy = _default_vs_new(self.extract_privacy, extract_privacy)

        base_url = 'https://www.facebook.com/ajax/browser/dialog/likes?id={photo_id}&__user={user_id}&__a=1'
        all_photos = []

        for photo_id in self.photos_fids:
            photo_url = base_url.format(photo_id=photo_id, user_id=user_id)
            self.driver.get(photo_url)
            current_photo = self.parse_photo_html(self.driver.page_source, extract_taggees,
                                  extract_likers, extract_commenters,
                                  extract_comments, extract_privacy)
            all_photos.append(current_photo)




if __name__ == '__main__':
    ph_parser = PhotoParser(['10151644807206335'])
    ph_parser.parse()