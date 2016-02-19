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

from datetime import datetime
from base64 import b64encode
from HTMLParser import HTMLParser

from selenium import webdriver
from lxml import html

import re, json
from mysql import connector
from fb_main import *
import fb_constants as constants

def _default_vs_new(default_val, new_val):
    """
    :param default_val: Default value
    :param new_val: New Value
    :return: new_val if not null, default otherwise
    """
    if new_val is not None:
        return new_val
    return default_val

class PhotoParser(FBParser):
    """
    Class to parse photo's metadata
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

    def parse_photo(self, photo_id, user_id, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_sharers=True, extract_comments=True, extract_privacy=True):
        """
        :param photo_html: Current photo HTML
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        :return: FBPhoto instance of current photo
        """

        taggees = likers = commenters = sharers = comments = privacy = None

        cur_picture = FBPicture(photo_id)

        if extract_likers:
            liker_parser = PhotoParser.FBPhotoLikerParser(self.driver)
            cur_picture.likers = liker_parser.parse_photo_likers(photo_id, user_id)

        if extract_taggees:
            taggee_parser = 1

        return cur_picture

    def run(self, email, password, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True):

        if self.driver is None:
            self.driver = webdriver.Chrome()

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

        all_photos = []

        for photo_id in self.photos_fids:
            current_photo = self.parse_photo(photo_id, user_id, extract_taggees, user_id,
                                  extract_likers, extract_commenters,
                                  extract_comments, extract_privacy)
            all_photos.append(current_photo)

        return all_photos

    def quit(self):
        self.driver.quit()

    class FBPhotoTaggeeParser(FBParser):
        """
        Parses a photo's taggees
        """
        pass
    class FBPhotoLikerParser(FBParser):
        """
        Parses a photo's likers
        """

        def __init__(self, driver):
            self.driver = driver

        def _parse_payload_from_ajax_response(self, ajax_response):
            """
            :param ajax_response: full response
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

        def _parse_fbuser_from_liker_element(self, user_element):
            """
            :param xpath_element: XPath element
            :return: FBUser instance of current element
            """
            username = full_name = fid = None

            fid_url = user_element.xpath(constants.FBXpaths.user_fid_url)
            if len(fid_url) > 0:
                fid = unicode(self._info_from_url('liker_fid_from_url', fid_url[0]))

            username_url = user_element.xpath(constants.FBXpaths.user_username_url)
            if len(username_url) > 0:
                username = unicode(self._info_from_url('liker_username_from_url', username_url[0]))
                if username in [u'profile.php', u'people']:
                    username = None

            full_name_result = user_element.xpath(constants.FBXpaths.user_full_name)
            if len(full_name_result) > 0:
                full_name = unicode(full_name_result[0])

            return FBUser(fid, full_name, username)

        def _get_likers_html(self, photo_id, user_id, liker_start=0):
            """
            :param photo_id: Photo fid
            :param user_id: Logged in user id
            :param liker_start: Index of liker to start parsing
            :return: relevant html containing likers
            """
            base_url = 'https://www.facebook.com/ajax/browser/dialog/likes?id={photo_id}&start={start}&__user={user_id}&__a=1'

            photo_url = base_url.format(photo_id=photo_id, user_id=user_id, start=liker_start)
            print photo_url
            self.driver.get(photo_url)
            page_source = self._parse_payload_from_ajax_response(self.driver.page_source)
            if page_source is None:
                return None
            fixed_payload = self._fix_payload(page_source)
            return fixed_payload

        def parse_photo_likers(self, photo_id, user_id):
            """
            :param photo_id: Photo's FID
            :param user_id: logged in user fid
            :return: List of FBUsers
            """

            if self.driver is None:
                self.driver = webdriver.Chrome()

            liker_nodes = []

            liker_start = 0

            html_payload = self._get_likers_html(photo_id, user_id, liker_start)
            tree = html.fromstring(html_payload)

            all_likers = tree.xpath(constants.FBXpaths.likers)
            while len(all_likers) > 0:
                print "Currently extracted: {0}".format(len(liker_nodes))
                print 'Ectracting now: {0}'.format(len(all_likers))
                for liker in all_likers:
                    current_liker = self._parse_fbuser_from_liker_element(liker)
                    if not current_liker in liker_nodes:
                        liker_nodes.append(current_liker)

                liker_start += len(all_likers)
                html_payload = self._get_likers_html(photo_id, user_id, liker_start)
                tree = html.fromstring(html_payload)
                all_likers = tree.xpath(constants.FBXpaths.likers)

            return liker_nodes


if __name__ == '__main__':
    ph_parser = PhotoParser(['10206326013841853'])
    res = ph_parser.run('sidfeiner@gmail.com', 'Qraaynem23')
    ph_parser.quit()
    for liker in res[0].likers:
        try:
            print liker
        except Exception, e:
            print type(liker.fid), type(liker.full_name)
            print str(e)

