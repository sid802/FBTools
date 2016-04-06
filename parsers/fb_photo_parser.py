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

from lxml import html

from parsers import fb_constants as constants
from fb_main import *
from fb_main import _default_vs_new
from fb_df import *
from datetime import datetime

class PhotoParser(FBParser):
    """
    Class to parse photo's metadata
    """

    def __init__(self, photos_fids=None, album_ids=None, extract_taggees=True, extract_likers=True, extract_commenters=True,
                 extract_comments=True, extract_privacy=True):
        """
        :param photos_fids: List of picture fb_ids
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        All options default to True
        """
        super(PhotoParser, self).__init__()
        self.photos_fids = photos_fids
        self.album_ids = album_ids
        self.extract_taggees = extract_taggees
        self.extract_likers = extract_likers
        self.extract_commenters = extract_commenters
        self.extract_comments = extract_comments
        self.extract_privacy = extract_privacy

    @FBParser.browser_needed
    def from_album(self, album_id):
        """
        :param album_id: Photo Album ID
                         When looking at the url param: set=a.10207797332908137.1073741831.1138852054
                         the album_id is 10207797332908137
        :returns: Adds relevant photo id's to self.photos_fids
        """

        pass



    @FBParser.browser_needed
    def parse_photo_meta(self, photo_id):
        """
        :param photo_id: Photo's FID
        :return: Picture's privacy setting (friends/friends of friends/publci etc), author, date published and caption
        """

        base_url = 'https://facebook.com/{photo_id}'
        current_url = base_url.format(photo_id=photo_id)
        self.driver.get(current_url)
        #print self.driver.page_source
        tree = html.fromstring(self.driver.page_source)

        author = privacy = pic_published = caption = None

        # Pic's Author
        author_result = tree.xpath(constants.FBXpaths.photo_author)
        if len(author_result) > 0:
            author = self._parse_user_from_link(author_result[0])

        # Pic's privacy
        privacy_result = tree.xpath(constants.FBXpaths.privacy_logged_in)
        if len(privacy_result) > 0:
            privacy = self._info_from_url('privacy', privacy_result[0])
        else:
            privacy_result = tree.xpath(constants.FBXpaths.privacy_not_logged_in)
            if len(privacy_result) > 0:
                privacy = self._info_from_url('privacy', privacy_result[0])

        # Pic's date published
        timestamp_match = constants.FBRegexes.picture_timestamp.search(self.driver.page_source)
        if timestamp_match is not None:
            timestamp = int(timestamp_match.group('result'))
            pic_published = datetime.fromtimestamp(timestamp)

        # Caption
        caption_match = tree.xpath(constants.FBXpaths.photo_caption_normal)
        if len(caption_match) == 0:
            caption_match = tree.xpath(constants.FBXpaths.photo_caption_theater)
        if len(caption_match) > 0:
            caption = ''.join(caption_match)

        return author, privacy, pic_published, caption


    def parse_photo(self, photo_id, user_id, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_sharers=True, extract_comments=True):
        """
        :param photo_html: Current photo HTML
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :return: FBPhoto instance of current photo
        """

        cur_picture = FBPicture(photo_id)

        cur_picture.author, cur_picture.privacy, cur_picture.published, cur_picture.caption = \
            self.parse_photo_meta(photo_id)  # Returns tuple of (author, privacy, date published, caption)

        if extract_likers:
            liker_parser = PhotoParser.FBPhotoLikerParser(self.driver)
            cur_picture.likers = liker_parser.parse_photo_likers(photo_id, user_id)

        if extract_taggees:
            taggee_parser = PhotoParser.FBPhotoTaggeeParser(self.driver)
            cur_picture.taggees = taggee_parser.parse_photo_taggees(photo_id, user_id)

        return cur_picture

    @FBParser.browser_needed
    def run(self, email, password, extract_taggees=True, extract_likers=True, extract_commenters=True,
              extract_comments=True, extract_privacy=True):
        """
        :param email: email to connect with
        :param password: password to connect with
        :param extract_taggees: Boolean, extract tagged people
        :param extract_likers: Boolean, extract likers
        :param extract_commenters: Boolean, extract commenters
        :param extract_comments: Boolean, extract comments
        :param extract_privacy: Boolean, extract privacy mode
        :return: List of FBPicture instances
        """

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

        all_photos = FBPictureList()

        for photo_id in self.photos_fids:
            current_photo = self.parse_photo(photo_id, user_id, extract_taggees,
                                  extract_likers, extract_commenters,
                                  extract_comments, extract_privacy)
            all_photos.append(current_photo)

        return all_photos

    class FBPhotoTaggeeParser(FBParser):
        """
        Parses a photo's taggees
        """

        def __init__(self, driver=None):
            self.driver = driver

        @FBParser.browser_needed
        def parse_photo_taggees(self, photo_id, user_id):
            """
            :param photo_id: Photo's FID
            :param user_id: logged in user fid
            :return: List of FBUsers who are tagged in the photo
            """
            taggee_nodes = FBUserList()

            html_payload = self._get_taggees_html(photo_id, user_id)
            try:
                tree = html.fromstring(html_payload)
            except Exception, e:
                print str(e)
                raise Exception()

            all_taggees = tree.xpath(constants.FBXpaths.user_taggee_links)
            if len(all_taggees) > 0:
                for taggee in all_taggees:
                    current_taggee = self._parse_user_from_link(taggee)
                    if not current_taggee in taggee_nodes:
                        taggee_nodes.append(current_taggee)

            return taggee_nodes

        def _get_taggees_html(self, photo_id, user_id, liker_start=0):
            """
            :param photo_id: Photo fid
            :param user_id: Logged in user id
            :param liker_start: Index of liker to start parsing
            :return: relevant html containing likers
            """
            base_url = 'https://www.facebook.com/ajax/pagelet/generic.php/PhotoViewerInitPagelet?data={{"fbid":"{photo_id}"}}&__user={user_id}&__a=1'

            photo_url = base_url.format(photo_id=photo_id, user_id=user_id)
            self.driver.get(photo_url)
            page_source = self._parse_payload_from_ajax_response(self.driver.page_source)
            #print 'after response parse:', page_source
            if page_source is None:
                return None
            fixed_payload = self._fix_payload(page_source)
            return fixed_payload


    class FBPhotoLikerParser(FBParser):
        """
        Parses a photo's likers
        """

        def __init__(self, driver):
            self.driver = driver

        def _get_likers_html(self, photo_id, user_id, liker_start=0):
            """
            :param photo_id: Photo fid
            :param user_id: Logged in user id
            :param liker_start: Index of liker to start parsing
            :return: relevant html containing likers
            """
            base_url = 'https://www.facebook.com/ajax/browser/dialog/likes?id={photo_id}&start={start}&__user={user_id}&__a=1'

            photo_url = base_url.format(photo_id=photo_id, user_id=user_id, start=liker_start)
            self.driver.get(photo_url)
            page_source = self._parse_payload_from_ajax_response(self.driver.page_source)
            if page_source is None:
                return None
            fixed_payload = self._fix_payload(page_source)
            return fixed_payload

        @FBParser.browser_needed
        def parse_photo_likers(self, photo_id, user_id):
            """
            :param photo_id: Photo's FID
            :param user_id: logged in user fid
            :return: List of FBUsers who liked the photo
            """
            liker_nodes = FBUserList()

            liker_start = 0

            html_payload = self._get_likers_html(photo_id, user_id, liker_start)
            #print html_payload
            tree = html.fromstring(html_payload)

            all_likers = tree.xpath(constants.FBXpaths.user_liker_links)
            while len(all_likers) > 0:
                for liker in all_likers:
                    current_liker = self._parse_user_from_link(liker)
                    if not current_liker in liker_nodes:
                        liker_nodes.append(current_liker)

                liker_start += len(all_likers)
                html_payload = self._get_likers_html(photo_id, user_id, liker_start)
                #print html_payload
                tree = html.fromstring(html_payload)
                all_likers = tree.xpath(constants.FBXpaths.user_liker_links)

            return liker_nodes


if __name__ == '__main__':
    #ph_parser = PhotoParser(['10207797509032540', '10153908354537528', '10153761999401335', '10153699836666335'], True, False, False, False, True)
    ph_parser = PhotoParser(['4632429683101'], None, True, False, False, False, True)


    email = raw_input('Enter Email: ')
    password = raw_input('Enter password: ')

    res = ph_parser.run(email, password)
    ph_parser.quit()

    res.plot_likers(kind='bar')

    print 'Likers:'
    for liker in res[0].likers:
        print liker

    print 'Taggees:'
    for taggee in res[0].taggees:
        print taggee

    print 'Privacy: {0}'.format(res[0].privacy)
    print 'Author: {0}'.format(res[0].author)
    print 'Published: {0}'.format(res[0].published)

