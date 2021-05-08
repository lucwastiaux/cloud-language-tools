import json
import requests
import tempfile
import logging
import os
import base64

import cloudlanguagetools.service
import cloudlanguagetools.constants
import cloudlanguagetools.ttsvoice
import cloudlanguagetools.translationlanguage
import cloudlanguagetools.transliterationlanguage
import cloudlanguagetools.errors


def get_audio_language_enum(voice_language):
    CereProc_audio_id_map = {
        'ar-MS': 'ar_XA'
    }
    language_enum_name = voice_language.replace('-', '_')
    if voice_language in CereProc_audio_id_map:
        language_enum_name = CereProc_audio_id_map[voice_language]
    return cloudlanguagetools.constants.AudioLanguage[language_enum_name]

class CereProcVoice(cloudlanguagetools.ttsvoice.TtsVoice):
    def __init__(self, voice_data):
        self.service = cloudlanguagetools.constants.Service.CereProc
        self.audio_language = get_audio_language_enum(voice_data['language'])
        self.name = voice_data['name']
        self.description = voice_data['description']
        self.description = voice_data['description']
        self.gender = cloudlanguagetools.constants.Gender[voice_data['gender'].capitalize()]


    def get_voice_key(self):
        return {
            'name': self.name
        }

    def get_voice_shortname(self):
        is_dnn = ''
        if 'Dnn' in self.description:
            is_dnn = ' (Dnn)'
        return self.description.split(':')[0] + is_dnn

    def get_options(self):
        return {}

class CereProcService(cloudlanguagetools.service.Service):
    def __init__(self):
        pass

    def configure(self):
        self.username = os.environ['CEREPROC_USERNAME']
        self.password = os.environ['CEREPROC_PASSWORD']
    

    def get_access_token(self):
        combined = f'{self.username}:{self.password}'
        auth_string = base64.b64encode(combined.encode('utf-8')).decode('utf-8')
        headers = {'authorization': f'Basic {auth_string}'}

        auth_url = 'https://api.cerevoice.com/v2/auth'
        response = requests.get(auth_url, headers=headers)

        access_token = response.json()['access_token']        
        return access_token
    
    def get_auth_headers(self):
        headers={'Authorization': f'Bearer {self.get_access_token()}'}
        return headers

    def get_translation_language_list(self):
        return []

    def list_voices(self):
        list_voices_url = 'https://api.cerevoice.com/v2/voices'
        
        response = requests.get(list_voices_url, headers=self.get_auth_headers())
        data = response.json()
        return data['voices']

    def get_tts_voice_list(self):
        result = []

        voice_list = self.list_voices()
        for voice in voice_list:
            print(voice)
            # try:
            #     result.append(CereProcVoice(voice))
            # except KeyError:
            #     logging.error(f'could not process voice for {voice}', exc_info=True)

        return result

    def get_tts_audio(self, text, voice_key, options):
        output_temp_file = tempfile.NamedTemporaryFile()
        output_temp_filename = output_temp_file.name

        base_url = self.speech_url
        url_path = '/v1/synthesize'
        voice_name = voice_key["name"]
        constructed_url = base_url + url_path + f'?voice={voice_name}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'audio/mp3'
        }

        data = {
            'text': text
        }

        response = requests.post(constructed_url, data=json.dumps(data), auth=('apikey', self.speech_key), headers=headers, timeout=cloudlanguagetools.constants.RequestTimeout)

        if response.status_code == 200:
            with open(output_temp_filename, 'wb') as audio:
                audio.write(response.content)
            return output_temp_file

        # otherwise, an error occured
        error_message = f"Status code: {response.status_code} reason: {response.reason} voice: [{voice_name}]]"
        raise cloudlanguagetools.errors.RequestError(error_message)


    def get_transliteration_language_list(self):
        return []
