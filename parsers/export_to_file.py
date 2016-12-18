__author__ = 'Sid'

################
#
# Write FB group
# users to file
#
################


from fb_main import blankify
from logging import Logger

_ACTION_AUTHOR = 1
_ACTION_COMMENTER = 2

_ACTION_DICT = {
    _ACTION_AUTHOR: 'author',
    _ACTION_COMMENTER: 'commenter'
}

NEW_RECORD_PREFIX = u'new_record '
NEWLINE = u"\r\n"

def encode_dict(dict, encoding='utf-8'):
    """
    :param dict: Dictionary 
    :return: Dictionary with keys and values unicode-ified
    """
    
    new_dict = {}
    for k, v in dict.iteritems():
        new_dict[k.encode(encoding)] = v.encode(encoding)
    return new_dict

def write_user_posts(user_posts, output_file):
    """
    :param users: iterator of user_posts we want to save
    :param output_file: handle to the file to write to
    :return: amount of users it successfully wrote
    """

    pass


def write_user_start(user, output_file):
    """
    :param user: User we start parsing
    :param output_file: File to write to
    :return:
    """
    _write_user_action(user, u'start', output_file)


def write_user_end(user, output_file):
    """
    :param user: User we ended parsing
    :param output_file: File to write to
    :return:
    """
    _write_user_action(user, u'end', output_file)


def _write_user_action(user, action, output_file):
    """
    :param user: UserInfo we write an action (start/end)
    :param action: start/end
    :param output_file: File to write to
    :return:
    """

    d = {
        u'action': action,
        u'u_id': user.fid,
        u'u_u_name': blankify(user.user_name),
        u'u_f_name': user.full_name
    }

    record = u"{action}_user\t{u_id}\t{u_u_name}\t{u_f_name}"
    _export_message(output_file, record, **d)


def write_group_start(group, output_file):
    """
    :param group: Group we start to parse
    :param output_file: File to write to
    :return:
    """
    _write_group_action(group, u'start', output_file)


def write_group_end(group, output_file):
    """
    :param group: Group we ended parsing
    :param output_file: File to write to
    :return:
    """
    _write_group_action(group, u'end', output_file)


def write_post_start(post, output_file):
    """
    :param post: Post we start parsing
    :param output_file: file to write to
    :return:
    """
    _write_post_action(post, u'start', output_file)


def write_post_end(post, output_file):
    """
    :param post: Post we end parsing
    :param output_file: file to write to
    :return:
    """
    _write_post_action(post, u'end', output_file)


def _export_message(output, record_fmt, encoding='utf-8', **fmt_dict):
    """
    :param output: Output object (file/logger)
    :param record_fmt: Record we want to write
    :param fmt_dict: Dictionary fillind the record_fmt
    """
    if isinstance(output, file):
        encoded_dict = encode_dict(fmt_dict, encoding)
        output.write((record_fmt + NEWLINE).format(**encoded_dict))
    elif isinstance(output, Logger):
        output.info((NEW_RECORD_PREFIX + record_fmt).format(**fmt_dict))

def _write_post_action(post, action, output_file, encoding='utf-8'):
    """
    :param post: Post we have an action for (start/end parsing)
    :param action: start/end
    :param output_file: file to write to
    :return:
    """

    if post.date_time is None:
        date_time = u''
    else:
        date_time = post.date_time.strftime(u"%d/%m/%Y %H:%M")

    d = {
        u'action': action,
        u'p_id': post.fid,
        u'g_id': post.group.fid,
        u'u_id': post.author.user.fid,
        u'p_time': date_time
    }

    record_fmt = u"{action}_post\t{p_id}\t{g_id}\t{u_id}\t{p_time}"
    _export_message(output_file, record_fmt, **d)




def _write_group_action(group, action, output_file, encoding='utf-8'):
    """
    :param group: Group we have an action for (start/end parsing)
    :param action: start/end
    :param output_file: file to write to
    :return:
    """
    
    d = {
        u'action': action,
        u'g_id': group.fid,
        u'g_name': group.title,
        u'g_user': blankify(group.username),
        u'g_member': group.members_amount,
        u'priv': blankify(group.privacy),
        u'desc': blankify(group.description),
        u'cat': blankify(group.category)
    }
    
    record = u"{action}_group\t{g_id}\t{g_name}\t{g_user}\t{g_member}\t{priv}\t{desc}\t{cat}"
    _export_message(output_file, record, **d)


def write_user_post(user_post, output_file):
    """
    :param user_post: FBPost to write
    :param output_file: File to write to
    :return:
    """

    write_post_start(user_post, output_file)  # user_id of author is written there

    write_user_infos(user_post.author, u'author', output_file)  # user_post.author is UserInfo instance
    for commenter in user_post.commenters:
        write_user_infos(commenter, u'commenter', output_file)  # commenter is UserInfo instance

    write_post_end(user_post, output_file)


def write_user_infos(user, action, output_file, encoding='utf-8'):
    """
    :param user: UserInfo we want to write
    :param action: author/commenter
    :param output_file: file to write to
    We MUST also write user_id because of the commenters. Author's user_id can be found be joining to the post
    """

    record = u"add_user\t{id}\t{user_name}\t{full_name}"
    
    d = {
        u'id': user.user.fid,
        u'user_name': blankify(user.user.user_name),
        u'full_name': user.user.full_name
    }

    _export_message(output_file, record, **d)


    if not user.infos:
        user.infos.add((u'', u'', u''))  # At least the user will be written

    for info in user.infos:
        
        d = {
            u'u_id': user.user.fid,
            u'action': action,
            u'i_kind': info[2],
            u'i_canonized': info[0],
            u'i_original': info[1]
        }
        
        record = u"add_info\t{u_id}\t{action}\t{i_kind}\t{i_canonized}\t{i_original}"
        _export_message(output_file, record, **d)


def write_absolute_parse(group, output_file):
    """
    :param group: Group instance we have absolutely parsed
    :param output_file: File to write to
    :return:
    Writes a command that group has absolutely been parsed
    """

    d = {u'id': group.fid}
    record = u"abs_parse\t{id}"
    _export_message(output_file, record, **d)
