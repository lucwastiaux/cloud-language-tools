import datetime
import cloudlanguagetools.constants

PATREON_MONTHLY_CHARACTER_LIMIT = 250000

TRIAL_USER_CHARACTER_LIMIT = 5000
TRIAL_EXTENDED_USER_CHARACTER_LIMIT = 50000

GETCHEDDAR_CHAR_MULTIPLIER = 1000.0

AZURE_CJK_CHAR_MULTIPLIER = 2
NAVER_AUDIO_CHAR_MULTIPLIER = 6

COST_TABLE = [
    # audio
    {
        'service': 'Azure',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16 * 1.255
    },
    {
        'service': 'Google',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16
    },
    {
        'service': 'Amazon',
        'request_type': 'audio',
        'character_cost': (1.0/1000000) * 16
    },                        
    {
        'service': 'Watson',
        'request_type': 'audio',
        'character_cost': (1.0/1000) * 0.02
    },
    {
        'service': 'Naver',
        'request_type': 'audio',
        'character_cost': ((1.0/1000) * 0.090) / NAVER_AUDIO_CHAR_MULTIPLIER
    },
    # translation
    {
        'service': 'Azure',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 10
    },
    {
        'service': 'Google',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 20
    },
    {
        'service': 'Amazon',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 15
    },            
    {
        'service': 'Watson',
        'request_type': 'translation',
        'character_cost': (1.0/1000) * 0.02
    },            
    {
        'service': 'Naver',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 17.70
    },            
    {
        'service': 'DeepL',
        'request_type': 'translation',
        'character_cost': (1.0/1000000) * 24.22
    },
    # transliteration
    {
        'service': 'Azure',
        'request_type': 'transliteration',
        'character_cost': (1.0/1000000) * 10
    },            

]

def adjust_character_count(
    service: cloudlanguagetools.constants.Service, 
    request_type: cloudlanguagetools.constants.RequestType,
    language: cloudlanguagetools.constants.Language,
    characters: int):
    
    azure_double_count_languages = [
            cloudlanguagetools.constants.Language.ja,
            cloudlanguagetools.constants.Language.ko,
            cloudlanguagetools.constants.Language.yue,
            cloudlanguagetools.constants.Language.zh_cn,
            cloudlanguagetools.constants.Language.zh_tw
        ]

    if language != None:
        if language in azure_double_count_languages:
            if service == cloudlanguagetools.constants.Service.Azure:
                if request_type == cloudlanguagetools.constants.RequestType.audio:
                    return characters * AZURE_CJK_CHAR_MULTIPLIER

    if service == cloudlanguagetools.constants.Service.Naver:
        if request_type == cloudlanguagetools.constants.RequestType.audio:
            return characters * NAVER_AUDIO_CHAR_MULTIPLIER

    return characters

class UsageSlice():
    def __init__(self, 
                request_type: cloudlanguagetools.constants.RequestType, 
                usage_scope: cloudlanguagetools.constants.UsageScope, 
                usage_period: cloudlanguagetools.constants.UsagePeriod, 
                service: cloudlanguagetools.constants.Service, 
                api_key: str,
                api_key_type: cloudlanguagetools.constants.ApiKeyType,
                api_key_data):
        self.request_type = request_type
        self.usage_scope = usage_scope
        self.usage_period = usage_period
        self.service = service
        self.api_key = api_key
        self.api_key_type = api_key_type
        self.api_key_data = api_key_data

    def build_key_suffix(self) -> str:
        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.recurring:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{self.api_key}'

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.lifetime:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{self.api_key}'

        date_str = datetime.datetime.today().strftime('%Y%m')
        if self.usage_period == cloudlanguagetools.constants.UsagePeriod.daily:
            date_str = datetime.datetime.today().strftime('%Y%m%d')

        api_key_suffix = ''
        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
            api_key_suffix = f':{self.api_key}'

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User and self.usage_period == cloudlanguagetools.constants.UsagePeriod.patreon_monthly:
            return f'{self.usage_scope.key_str}:{self.usage_period.name}:{date_str}{api_key_suffix}'

        return f'{self.usage_scope.key_str}:{self.usage_period.name}:{date_str}:{self.service.name}:{self.request_type.name}{api_key_suffix}'


    def over_quota(self, characters, requests) -> bool:
        # print(f'over_quota: usage_period: {self.usage_period} api_key_type: {self.api_key_type}')
        if self.api_key_type == cloudlanguagetools.constants.ApiKeyType.getcheddar:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.recurring:
                if self.api_key_data['thousand_char_overage_allowed'] == 1:
                    # overages allowed, don't restrict
                    return False
                total_chars = GETCHEDDAR_CHAR_MULTIPLIER * self.api_key_data['thousand_char_used'] + characters
                allowed_chars = GETCHEDDAR_CHAR_MULTIPLIER * self.api_key_data['thousand_char_quota']
                # print(f'total_chars: {total_chars} allowed_chars: {allowed_chars}')
                if total_chars > allowed_chars:
                    return True
            # don't run through other checks for getcheddar users
            return False

        if self.api_key_type == cloudlanguagetools.constants.ApiKeyType.patreon:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.patreon_monthly:
                if characters > PATREON_MONTHLY_CHARACTER_LIMIT:
                    return True
            # don't run through other checks for patreon users
            return False

        if self.usage_scope == cloudlanguagetools.constants.UsageScope.User:
            if self.usage_period == cloudlanguagetools.constants.UsagePeriod.lifetime:
                character_limit = self.api_key_data.get('character_limit', None)
                if character_limit != None:
                    if characters > character_limit:
                        return True

        return False


