#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

from __future__ import with_statement
import os.path
import time
import random
import pickle
from wc import wc
import logging

post_path = None

def post_tweet(
    shorten_url=1,
    serialize=1,
    text='',
    latitude='0',
    longitude='0',
    base_url='',
    action='',
    tweet_id='0'):
    """
    Queue a status update.

    shorten_url: A boolean indicating whether to shorten any URLs
        embedded in text.  If true, text is searched for any URLs
        and they are shortened using the configured URL shortener.

    serialize: A boolean indicating whether to send the tweet as
        multiple status updates if the length of text exceeds the
        single tweet limit.

    text: The body of the tweet.

    latitude, longitude: The latitude and longitude of where the
       status update was made

    base_url: Meaning depends on the value of 'action':

       If 'twitpic': the filename of the picture to tweet.

       If 'tweet': ''.

       If 'reply': the base url of the tweet to which this tweet
           is a reply.

       If 'retweet', 'delete', 'favorite', 'follow' or 'unfollow':
           the base url of the account.

    action: 'twitpic', 'tweet', 'reply', 'retweet', 'delete',
      'favorite', 'follow'

    tweet_id: If action is 'retweet', 'delete' or 'favorite', the
       tweet id of the tweet in question.

       If action is 'follow' or 'unfollow': the user id or the
           screen name of the user to follow.

       Otherwise, ''.

    The status update will actually be sent when do_posts is
    called.
    """

    global post_path
    if post_path is None:
        post_path = os.path.join(
            os.path.expanduser('~'), '.khweeteur', 'topost')

    if not os.path.exists(post_path):
        try:
            os.makedirs(post_path)
        except IOError, e:
            logging.exception('post_tweet: creating directory %s: %s'
                              % (post_path, e))

    filename = os.path.join(
        post_path, str(time.time()) + '-' + str (random.random()))
    with open(filename, 'wb') as fhandle:
        post = {
            'shorten_url': shorten_url,
            'serialize': serialize,
            'text': text,
            'latitude': latitude,
            'longitude': longitude,
            'base_url': base_url,
            'action': action,
            'tweet_id': tweet_id,
            }
        pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)

    # Register the post with Woodchuck.
    if wc().available():
        try:
            if len(text) > 25:
                human_readable_name = text[:23] + "..."
            else:
                human_readable_name = text

            wc()['topost'].object_register(
                object_identifier=os.path.basename(filename),
                human_readable_name=human_readable_name,
                expected_size=-1 * os.path.getsize(filename))
        except Exception:
            logging.exception("Registering post %s with Woodchuck"
                              % (filename,))
