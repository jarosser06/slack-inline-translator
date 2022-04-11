'''Hermes Commands'''
import abc

from database import Database

AVAILABLE_LANGUAGES = {'ARABIC': 'ar',
                       'CHINESE': 'zh',
                       'CZECH': 'cs',
                       'DANISH': 'da',
                       'DUTCH': 'nl',
                       'ENGLISH': 'en',
                       'FINNISH': 'fi',
                       'FRENCH': 'fr',
                       'GERMAN': 'de',
                       'HEBREW': 'he',
                       'HINDI': 'hi',
                       'INDONESIAN': 'id',
                       'ITALIAN': 'it',
                       'JAPANESE': 'ja',
                       'KOREAN': 'ko',
                       'MALAY': 'ms',
                       'NORWEGIAN': 'no',
                       'PERSIAN': 'fa',
                       'POLISH': 'pl',
                       'PORTUGUESE': 'pt',
                       'RUSSIAN': 'ru',
                       'SPANISH': 'es',
                       'SWEDISH': 'sv',
                       'TURKISH': 'tr'}


class Command(object):
    '''Base Class for Commands'''
    def __init__(self, name, description, arguments=[]):
        self.name = name
        self.description = description
        self.arguments = arguments

    def parse_args(self, full_cmd):
        '''Overridable method to allow individual command to parse arguments'''
        return {}

    def match(self, txt):
        return self.name == txt

    @abc.abstractmethod
    def run(self, **kwargs):
        pass


class SetLanguage(Command):
    def __init__(self):
        self.name = "set language"
        self.description = "Set preferred language"
        self.arguments = ['language']

    def parse_args(self, full_cmd):
        lang = full_cmd.split(' ')[-1]
        return {'language': lang}

    def match(self, txt):
        return self.name in txt

    def run(self, **kwargs):
        user_id = kwargs['user_id']
        dynamodb_table = kwargs['dynamodb_table']
        workspace = kwargs['team']
        lang = AVAILABLE_LANGUAGES.get(kwargs['language'].upper())

        if not lang:
            return "Invalid language"

        Database(dynamodb_table).set_user_preference(
            workspace,
            user_id,
            lang,
        )
        return "Language set to " + kwargs['language'].capitalize()


class GetLanguage(Command):
    def __init__(self):
        self.name = "get language"
        self.description = "Get preferred language"
        self.arguments = []

    def run(self, **kwargs):
        user_id = kwargs['user_id']
        dynamodb_table = kwargs['dynamodb_table']
        workspace = kwargs['team']
        result = Database(dynamodb_table).get_user_preference(
            workspace,
            user_id,
        )
        if not result:
            return "None set"

        '''Inverse AVAILABLE_LANGUAGES to lookup by value and get HR Result'''
        inv_lang_map = {v: k for k, v in AVAILABLE_LANGUAGES.items()}
        return "Language set to " + inv_lang_map[result].capitalize()


class ListLanguages(Command):
    def __init__(self):
        self.name = "list languages"
        self.description = "List all available languages"
        self.arguments = []

    def run(self, **kwargs):
        return ', '.join(
            [key.capitalize() for key in AVAILABLE_LANGUAGES.keys()])


class Commander(object):
    def __init__(self, *commands):
        self.commands = commands

    def help(self):
        txt = ["help - Display this help message"]
        for cmd in self.commands:
            args = ' '.join(["<{}>".format(arg) for arg in cmd.arguments])
            cmd_name = cmd.name + ' ' + args
            txt.append(cmd_name + ' - ' + cmd.description)

        return '\n'.join(txt)

    def _load_command(self, command_name):
        for cmd in self.commands:
            if cmd.match(command_name):
                return cmd

        return None

    def execute_command(self, command, **kwargs):
        '''Execute given command with arguments'''
        if command == 'help':
            return self.help()

        loaded_command = self._load_command(command)
        if not loaded_command:
            return "Command not found :( \n\n {}".format(self.help())

        return loaded_command.run(**{**kwargs,
                                     **loaded_command.parse_args(command)})


LoadedCommander = Commander(SetLanguage(),
                            GetLanguage(),
                            ListLanguages())
