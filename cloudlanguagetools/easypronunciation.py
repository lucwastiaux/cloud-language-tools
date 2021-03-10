import os
import requests
import urllib.parse

import cloudlanguagetools.service
import cloudlanguagetools.constants
import cloudlanguagetools.transliterationlanguage

class EasyPronunciationTransliterationLanguage(cloudlanguagetools.transliterationlanguage.TransliterationLanguage):
    def __init__(self, url_path, language, api_params, api_key):
        self.service = cloudlanguagetools.constants.Service.EasyPronunciation
        self.url_path = url_path
        self.language = language
        self.api_params = api_params
        self.api_key = api_key

    def get_transliteration_name(self):
        result = f'{self.language.lang_name} (IPA Pronunciation), {self.service.name}'
        return result

    def get_transliteration_key(self):
        return {
            'url_path': self.url_path,
            'api_params': self.api_params,
            'api_key': self.api_key
        }

class EasyPronunciationService(cloudlanguagetools.service.Service):
    def __init__(self):
        self.url_base = 'https://easypronunciation.com'

    def configure(self):
        self.api_keys = {
            'french': os.environ['EASYPRONUNCIATION_FRENCH'],
            'english': os.environ['EASYPRONUNCIATION_ENGLISH'],
            'italian': os.environ['EASYPRONUNCIATION_ITALIAN'],
            'portuguese': os.environ['EASYPRONUNCIATION_PORTUGUESE'],
            'japanese': os.environ['EASYPRONUNCIATION_JAPANESE'],
            'spanish': os.environ['EASYPRONUNCIATION_SPANISH']
        }

    def get_tts_voice_list(self):
        return []

    def get_translation_language_list(self):
        return []

    def get_transliteration_language_list(self):
        result = [
            EasyPronunciationTransliterationLanguage('/french-api.php', cloudlanguagetools.constants.Language.fr,
            {
                'version': 1,
                'use_un_symbol': 1,
                'vowel_lengthening':1,
                'show_rare_pronunciations':0,
                'french_liaison_styling': 'one_by_one',
                'spell_numbers':1
            }, 'french'),
        ]
        return result

    def get_transliteration(self, text, transliteration_key):
        api_url = self.url_base + transliteration_key['url_path']
        parameters = {
            'access_token': self.api_keys[transliteration_key['api_key']],
            'phrase': text
        }
        parameters.update(transliteration_key['api_params'])
        encoded_parameters = urllib.parse.urlencode(parameters)
        full_url = f'{api_url}?{encoded_parameters}'

        # print(full_url)
        request = requests.get(full_url)
        result = request.json()

        # print(request)
        # print(result)

        if 'phonetic_transcription' in result:
            phonetic_transcription = result['phonetic_transcription']
            result_components = []
            for entry in phonetic_transcription:
                result_components.append(entry['transcriptions'][0])

            return ' '.join(result_components)

        # an error occured
        error_message = f'EasyPronunciation: could not perform conversion: {str(result)}'
        raise cloudlanguagetools.errors.RequestError(error_message)
