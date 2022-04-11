'''
Primary API
'''
import json
import logging
import os
import traceback

from functools import wraps

import boto3
import slack

# Local Imports
from slacker import (SlackMessageChannelType,
                     SlackEvent,
                     SlackRequest,
                     InvalidSlackRequest)

from commands import LoadedCommander
from database import Database


SNS_TOPIC_ENV_KEY = 'TRANSLATE_SNS_TOPIC'
SLACK_WORKSPACE = os.getenv('SLACK_WORKSPACE')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')


LOG = logging.getLogger()
LOG.setLevel(logging.getLevelName(LOG_LEVEL))


def api_response(handler):
    '''API Decorator To Handle API responses'''
    @wraps(handler)
    def wrapper(event, context):
        LOG.debug("Recieved event for: {}".format(event))
        try:
            body = handler(event, context)
        except InvalidSlackRequest:
            LOG.error("Slack request validation failed")
            return {'statusCode': 400, 'body': 'Invalid Request'}
        except Exception as exception:
            # Log the error and return a 500
            LOG.error("Exception occurred: {}".format(exception))
            traceback.print_exc()
            return {'statusCode': 500, 'body': 'Internal Error Occurred'}
        LOG.debug("No exceptions thrown, responding with 200!!!!")
        return {'statusCode': 200,
                'headers': {'content-type': 'application/json'},
                'body': body}
    return wrapper


def _translator_command(event, team):
    cmd_result = LoadedCommander.execute_command(event.text,
                                                 user_id=event.user,
                                                 dynamodb_table=DYNAMODB_TABLE,
                                                 team=team)

    sl_client = slack.WebClient(token=os.environ['BOT_OAUTH_TOKEN'])
    resp = sl_client.chat_postEphemeral(
        channel=event.channel,
        text=cmd_result,
        user=event.user)
    assert resp['ok']


@api_response
def slack_handler(event, context):
    '''
    Slack Handler

    /slack
    '''
    LOG.debug("Recieved event: {}".format(event))

    slack_event = event['body']
    req_headers = event['headers']
    signing_secret = os.environ['SLACK_SIGNING_SECRET']

    slack_request = SlackRequest(headers=req_headers,
                                 request=slack_event,
                                 signing_secret=signing_secret)

    '''Check for valid slack request'''
    LOG.info('Validating Slack Request')
    slack_request.validate()

    LOG.info("Slack request validated")
    slack_event = json.loads(slack_event)

    # Handle Challenge response from slack
    if 'challenge' in slack_event:
        return json.dumps({'challenge': slack_event['challenge']})

    LOG.debug("Slack Event: {}".format(slack_event))
    loaded_event = SlackEvent(slack_event['event'])
    slack_team = slack_event['team_id']

    LOG.info("Slack event loaded")
    msg_type = loaded_event.message_type
    LOG.info("Message was of type {}".format(msg_type))
    if loaded_event.message_type == SlackMessageChannelType.DIRECT_MESSAGE:
        LOG.info("Hermes recieved a direct message from user {}".format(
            loaded_event.user))
        _translator_command(loaded_event, slack_team)
        return "Fin"

    LOG.info("Hermes got message event from a public channel")

    sl_client = slack.WebClient(token=os.environ['BOT_OAUTH_TOKEN'])

    # TODO: Handle pagination
    channel_users = []
    chan_members = sl_client.conversations_members(
        channel=loaded_event.channel)
    LOG.debug("Retrieved Channel Members: {}".format(chan_members))
    channel_users = chan_members['members']

    db = Database(DYNAMODB_TABLE)
    member_preferences = db.get_users_preference(slack_team, channel_users)

    LOG.debug("Channel {} member preferences: {}".format(
        loaded_event.channel, member_preferences))

    message_language = 'en'
    # Hacky but assuming language is enlish if less than 20 chars
    if len(loaded_event.text) >= 20:
        comp_res = boto3.client('comprehend').detect_dominant_language(
            Text=loaded_event.text,
        )
        message_language = comp_res['Languages'][0]['LanguageCode']
        LOG.debug("Detected language is " + message_language)

    sns_client = boto3.client('sns')
    sns_topic_arn = os.environ[SNS_TOPIC_ENV_KEY]
    LOG.debug("Got member preferences: {}".format(member_preferences))

    for chan_member, preference in member_preferences:
        LOG.debug("Channel member {} has preference {}".format(
            chan_member, preference))
        '''Ignore the original speaker'''
        if loaded_event.user == chan_member:
            continue

        if preference != message_language:
            LOG.debug("Chan member {} not match message lang".format(
                chan_member))
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Message=json.dumps({
                    'user_id': chan_member,
                    'target_language': preference,
                    'workspace': slack_team,
                    'text': loaded_event.text,
                    'channel': loaded_event.channel,
                    'source_language': message_language,
                })
            )

    return "Fin"


def translate(event, context):
    '''
    Translate Text pulled off of an SNS topic

    Expects Message Body:
    {'user_id': <Slack User ID>,
     'target_language': <Target User Language>,
     'workspace': <Slack Workspace/Team>,
     'text': <Text to be translated,
     'channel': <Channel message was posted to>}
    '''
    LOG.debug("Recieved event: {}".format(event))

    records = event.get('Records')
    for record in records:
        sns_message = record.get('Sns')
        if not sns_message:
            LOG.warn('Translate must come from SNS')

        message = sns_message.get('Message')
        if not message:
            raise Exception('Translate: Empty message Recieved')

        msg_json = json.loads(message)

        translator = boto3.client(service_name='translate')
        translation = translator.translate_text(
            Text=msg_json['text'],
            SourceLanguageCode=msg_json['source_language'],
            TargetLanguageCode=msg_json['target_language'],
        )['TranslatedText']

        sl_client = slack.WebClient(token=os.environ['BOT_OAUTH_TOKEN'])
        resp = sl_client.chat_postEphemeral(
            channel=msg_json['channel'],
            text=translation,
            user=msg_json['user_id'],
        )
        assert resp['ok']
