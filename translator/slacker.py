'''Slack API'''
import hashlib
import hmac
import json
import logging
import urllib

import requests

from enum import Enum

'''
token=gIkuvaNzQIHlkjlg97ATvDxqgjtO
&team_id=T0001
&team_domain=example
&enterprise_id=E0001
&enterprise_name=Globular%20Construct%20Inc
&channel_id=C2147483705
&channel_name=test
&user_id=U2147483697
&user_name=Steve
&command=/weather
&text=94070
&response_url=https://hooks.slack.com/commands/1234/5678
&trigger_id=13345224609.738474920.8088930838d88f008e0
'''

LOG = logging.getLogger()


class InvalidSlackRequest(Exception):
    def __init__(self):
        self.message = "invalid slack request"


class SlackResponseType(Enum):
    EPHEMERAL = 'ephemeral'
    IN_CHANNEL = 'in_channel'


class SlackRequest(object):
    def __init__(self, **kwargs):
        '''initialize slack request'''
        self.headers = kwargs['headers']
        self.request_body = kwargs['request']
        self.slack_signing_secret = kwargs['signing_secret']

        props = urllib.parse.parse_qs(self.request_body)
        for prop in props:
            setattr(self, prop, props[prop][0])

        if hasattr(self, 'text'):
            inp = self.text.split(' ')
            self.sub_command = inp[0]
            self.sub_command_args = inp[1:]

    def validate(self):
        '''
        Check if Slack request is valid based on signature.
        https://api.slack.com/docs/verifying-requests-from-slack
        '''

        slack_request_timestamp = self.headers['X-Slack-Request-Timestamp']
        slack_signing_secret = bytes(self.slack_signing_secret,
                                     'utf-8')
        request_body = self.request_body
        slack_signature = self.headers['X-Slack-Signature']

        basestring = f"v0:{slack_request_timestamp}:{request_body}".encode(
            'utf-8')

        ''' Create a new HMAC "signature", and return the string. '''
        my_signature = 'v0=' + hmac.new(slack_signing_secret, basestring,
                                        hashlib.sha256).hexdigest()

        if not hmac.compare_digest(my_signature, slack_signature):
            raise InvalidSlackRequest

    def respond(self, text, attachments=[],
                response_type=SlackResponseType.EPHEMERAL):
        '''Send response to slack'''
        if not hasattr(self, 'response_url'):
            raise Exception(
                'Unable to respond to SlackRequest, no response_url')

        headers = {'Content-type': 'application/json'}
        resp_body = {
            'response_type': response_type,
            'text': text,
        }
        if attachments:
            resp_body['attachments'] = attachments

        requests.post(self.response_url,
                      data=json.dumps(resp_body),
                      headers=headers)


class SlackMessageChannelType(Enum):
    PRIVATE_CHANNEL = 'private_channel'
    PUBLIC_CHANNEL = 'public_channel'
    DIRECT_MESSAGE = 'direct_message'
    MULTI_DIRECT_MESSAGE = 'multi_direct_message'
    APP_MESSAGE = 'app_message'


class SlackEvent(object):
    def __init__(self, event_body):
        self.event_type = event_body['type']

        ''' Set Attrs lazily :)'''
        for key in ('subtype', 'text', 'client_msg_id', 'user', 'channel',
                    'event_ts', 'ts', 'channel_type'):
            setattr(self, key, event_body.get(key))

    @property
    def message_type(self):
        '''Return what type of message the event belongs to'''
        responses = {'group': SlackMessageChannelType.PRIVATE_CHANNEL,
                     'im': SlackMessageChannelType.DIRECT_MESSAGE,
                     'mpim': SlackMessageChannelType.MULTI_DIRECT_MESSAGE,
                     'app_home': SlackMessageChannelType.APP_MESSAGE,
                     'channel': SlackMessageChannelType.PUBLIC_CHANNEL}

        return responses[self.channel_type]
