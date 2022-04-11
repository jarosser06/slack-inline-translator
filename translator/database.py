'''
DynamoDB Interface for Hermes
'''

import boto3

DEFAULT_USER_KEY = '_default'
DEFAULT_LANG = 'en'


class Database(object):
    '''Handle fetching persistent data'''
    def __init__(self, table_name):
        self.table_name = table_name
        self._dynamodb = boto3.resource('dynamodb')
        self._table = self._dynamodb.Table(self.table_name)

    def add_workspace(self, workspace_name, default_language):
        '''Add new workspace to DynamoDB Table'''
        self._table.put_item(Item={'workspace': workspace_name,
                                   'user': DEFAULT_USER_KEY,
                                   'language': default_language})

    def get_user_preference(self, workspace_name, user_id):
        '''Fetch single user Preference'''
        resp = self._table.get_item(
            Key={
                'workspace': workspace_name,
                'user': user_id,
            }
        )
        return resp.get('Item', {}).get('preferred_language')

    def get_users_preference(self, workspace_name, user_ids):
        '''Get multiple User Preferences'''
        keys = [{'workspace': workspace_name, 'user': uid} for uid in user_ids]
        keys.append({'workspace': workspace_name, 'user': DEFAULT_USER_KEY})

        resp = self._dynamodb.batch_get_item(
            RequestItems={self.table_name: {'Keys': keys}}
        )

        results = []

        default_lang = DEFAULT_LANG
        for preference in resp['Responses'][self.table_name]:
            if preference['user'] == DEFAULT_USER_KEY:
                default_lang = preference['preferred_language']
                continue

            results.append((preference['user'],
                            preference['preferred_language']))

        '''Determine what users do not have preferences set'''
        notset_users = set(user_ids).difference(
            set(r[0] for r in results)
        )

        '''For every user with no preference, set the default'''
        for user in notset_users:
            results.append((user, default_lang))
        return results

    def set_user_preference(self, workspace_name, user_id, langauge):
        self._table.update_item(
            Key={
                'workspace': workspace_name,
                'user': user_id,
            },
            UpdateExpression="set preferred_language = :l",
            ExpressionAttributeValues={
                ':l': langauge,
            },
        )
