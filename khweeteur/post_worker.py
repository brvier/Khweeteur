#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''Worker to post tweets'''

from utils import *
import twitter
import re

if not USE_PYSIDE:
    from PyQt4.QtCore import QThread,QSettings
else:
    from PySide.QtCore import QThread,QSettings

class KhweeteurActionWorker(QThread):

    '''ActionWorker : Post tweet in background'''

    info = pyqtSignal(unicode)
    warn = pyqtSignal(unicode)
    pictUploaded = pyqtSignal(unicode)
    tweetSent = pyqtSignal()

    def __init__(
        self,
        parent=None,
        action=None,
        data=(None,None,None,None,None),
        ):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.action = action
        self.data = data[0]
        self.tb_text_replyid = data[1]
        self.tb_text_replytext = data[2]
        self.tb_text_replysource = data[3]
        self.geolocation = data[4]

    def run(self):
        '''Run the background thread'''

        if self.action == 'tweet':
            self.tweet()
        elif self.action == 'retweet':
            self.retweet()
        elif self.action == 'twitpic':
            self.twitpic_upload()

    def twitpic_upload(self):
        import twitpic
        import oauth2 as oauth
        import simplejson

        try:
            api = \
                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                    access_token_key=str(self.settings.value('twitter_access_token_key'
                    )),
                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                    )))
                    
            twitpic_client = twitpic.TwitPicOAuthClient(
                consumer_key = KHWEETEUR_TWITTER_CONSUMER_KEY,
                consumer_secret = KHWEETEUR_TWITTER_CONSUMER_SECRET,
                access_token = api._oauth_token.to_string(),
                service_key = 'f9b7357e0dc5473df5f141145e4dceb0'
                )
            
            # methods - read, create, update, remove
            params = {}
            print self.data[0]
            params['media'] = 'file://'+self.data[0]
            print params
            params['message'] = self.data[1] #(unicode(self.tb_text.toPlainText()).encode('utf-8'))
            response = twitpic_client.create('upload', params)
            print response
            #data = simplejson.loads(response)
            
            if response.has_key('url'):
                self.info.emit('Image successfully posted on TwitPic as ' + response['url'])
#                self.tb_text.insertPlainText()
                self.pictUploaded.emit(response['url'])

        except twitpic.TwitPicError, err:
            self.warn.emit('An error occur while posting image on TwitPic : '+err.reason)                                    
        except:
            #FIXME
            import traceback
            traceback.print_exc()
            self.warn.emit('An error occur while posting image on TwitPic')
         
    def tweet(self):
        '''Post a tweet'''

        try:
            status_text = self.data

            if int(self.settings.value('useBitly')) == 2:
                urls = re.findall("(?P<url>https?://[^\s]+)",
                                  status_text)
                if len(urls) > 0:
                    import bitly
                    a = bitly.Api(login='pythonbitly',
                                  apikey='R_06871db6b7fd31a4242709acaf1b6648'
                                  )

                for url in urls:
                    try:
                        short_url = a.shorten(url)
                        status_text = status_text.replace(url,
                                short_url)
                    except:
                        pass

            if not status_text.startswith(self.tb_text_replytext):
                self.tb_text_replyid = 0
                self.tb_text_replytext = ''
                self.tb_text_replysource = ''

            if self.geolocation:
                (latitude, longitude) = self.geolocation
            else:
                (latitude, longitude) = (None, None)

            if 'twitter' in self.tb_text_replysource \
                or self.tb_text_replyid == 0:
                if bool(int(self.settings.value('twitter_access_token'))):
                    api = \
                        twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                    api.SetUserAgent('Khweeteur')
                    if int(self.settings.value('useSerialization')) \
                        == 2:
                        api.PostSerializedUpdates(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    else:
                        api.PostUpdate(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    self.info.emit('Tweet sent to Twitter')

            if 'http://identi.ca/api' == self.tb_text_replysource \
                or self.tb_text_replyid == 0:
                if bool(int(self.settings.value('identica_access_token'))):
                    api = twitter.Api(base_url='http://identi.ca/api',
                            username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                            password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                            access_token_key=str(self.settings.value('identica_access_token_key'
                            )),
                            access_token_secret=str(self.settings.value('identica_access_token_secret'
                            )))
                    api.SetUserAgent('Khweeteur')
                    if int(self.settings.value('useSerialization')) \
                        == 2:
                        api.PostSerializedUpdates(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    else:
                        api.PostUpdate(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    self.info.emit('Tweet sent to Identica')

            self.tweetSent.emit()
        except twitter.TwitterError, e:

            self.warn.emit(e.message)
            print e.message
        except:
            self.warn.emit('A network error occur')
            print 'A network error occur'
            import traceback
            traceback.print_exc()
