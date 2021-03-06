import sys
import logging
import unittest
import secrets
import cloudlanguagetools
import cloudlanguagetools.servicemanager
from cloudlanguagetools.constants import Language
from cloudlanguagetools.constants import Service
import cloudlanguagetools.errors

def get_manager():
    manager = cloudlanguagetools.servicemanager.ServiceManager(secrets.config)
    manager.configure()    
    return manager

class TestTranslation(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                            datefmt='%Y%m%d-%H:%M:%S',
                            stream=sys.stdout,
                            level=logging.DEBUG)

        self.manager = get_manager()
        self.language_list = self.manager.get_language_list()
        self.translation_language_list = self.manager.get_translation_language_list_json()
        self.transliteration_language_list = self.manager.get_transliteration_language_list_json()

    def test_language_list(self):
        self.assertTrue(len(self.language_list) > 0)
        # check for the presence of a few languages
        self.assertEqual('French', self.language_list['fr'])
        self.assertEqual('Chinese (Simplified)', self.language_list['zh_cn'])
        self.assertEqual('Thai', self.language_list['th'])
        self.assertEqual('Chinese (Cantonese, Traditional)', self.language_list['yue'])
        self.assertEqual('Chinese (Traditional)', self.language_list['zh_tw'])

    def test_detection(self):
        source_text = 'Je ne suis pas intéressé.'
        self.assertEqual(Language.fr, self.manager.detect_language([source_text]))

        source_list = [
        'Pouvez-vous me faire le change ?',
        'Pouvez-vous débarrasser la table, s\'il vous plaît?',
        "I'm not interested"
        ]    
        # french should still win
        self.assertEqual(Language.fr, self.manager.detect_language(source_list))

        # chinese
        self.assertEqual(Language.zh_cn, self.manager.detect_language(['我试着每天都不去吃快餐']))

        # chinese traditional (most cantonese text will be recognized as traditional/taiwan)
        self.assertEqual(Language.zh_tw, self.manager.detect_language(['你住得好近一個機場']))
        

    def test_translate(self):
        source_text = 'Je ne suis pas intéressé.'
        translated_text = self.manager.get_translation(source_text, cloudlanguagetools.constants.Service.Azure.name, 'fr', 'en')
        self.assertEqual(translated_text, "I'm not interested.")

    def test_translate_error(self):
        source_text = 'Je ne suis pas intéressé.'
        self.assertRaises(cloudlanguagetools.errors.RequestError, self.manager.get_translation, source_text, cloudlanguagetools.constants.Service.Azure.name, 'fr', 'zh_cn')

    def translate_text(self, service, source_text, source_language, target_language, expected_result):
        source_language_list = [x for x in self.translation_language_list if x['language_code'] == source_language.name and x['service'] == service.name]
        self.assertEqual(1, len(source_language_list))
        target_language_list = [x for x in self.translation_language_list if x['language_code'] == target_language.name and x['service'] == service.name]
        self.assertEqual(1, len(target_language_list))

        from_language_key = source_language_list[0]['language_id']
        to_language_key = target_language_list[0]['language_id']

        # now, translate
        translated_text = self.manager.get_translation(source_text, service.name, from_language_key, to_language_key)
        self.assertEqual(expected_result, translated_text)

    def test_translate_chinese(self):
        # pytest test_translation.py -k test_translate_chinese
        self.translate_text(Service.Azure, '送外卖的人', Language.zh_cn, Language.en, 'The person who sent the takeaway')
        self.translate_text(Service.Google, '中国有很多外国人', Language.zh_cn, Language.en, 'There are many foreigners in China')
        self.translate_text(Service.Azure, '成本很低', Language.zh_cn, Language.fr, 'Le coût est très faible')
        self.translate_text(Service.Google, '换登机牌', Language.zh_cn, Language.fr, "Changer la carte d'embarquement")
        self.translate_text(Service.Amazon, '换登机牌', Language.zh_cn, Language.fr, "Changement de carte d'embarquement")

    def test_translate_chinese_watson(self):
        self.translate_text(Service.Watson, '中国有很多外国人', Language.zh_cn, Language.en, 'There are a lot of foreigners in China.')

    def test_translate_naver(self):
        # pytest test_translation.py -k test_translate_naver
        self.translate_text(Service.Naver, '천천히 말해 주십시오', Language.ko, Language.en, 'Please speak slowly.')
        self.translate_text(Service.Naver, 'Please speak slowly', Language.en, Language.ko, '천천히 말씀해 주세요')

        self.translate_text(Service.Naver, '천천히 말해 주십시오', Language.ko, Language.fr, 'Parlez lentement.')
        self.translate_text(Service.Naver, 'Veuillez parler lentement.', Language.fr, Language.ko, '천천히 말씀해 주세요.')        

    def test_translate_naver_unsupported_pair(self):
        # pytest test_translation.py -k test_translate_naver_unsupported_pair
        self.assertRaises(cloudlanguagetools.errors.RequestError, self.translate_text, Service.Naver, 'Veuillez parler lentement.', Language.fr, Language.th, 'Please speak slowly.')

    def test_translate_deepl(self):
        # pytest test_translation.py -rPP -k test_translate_deepl
        self.translate_text(Service.DeepL, 'Please speak slowly', Language.en, Language.fr, 'Veuillez parler lentement')
        self.translate_text(Service.DeepL, 'Je ne suis pas intéressé.', Language.fr, Language.en, """I'm not interested.""")
        self.translate_text(Service.DeepL, '送外卖的人', Language.zh_cn, Language.en, 'delivery person')


    def test_translate_all(self):
        # pytest test_translation.py -rPP -k test_translate_all
        # pytest test_translation.py --capture=no --log-cli-level=INFO -k test_translate_all

        source_text = '成本很低'
        from_language = Language.zh_cn.name
        to_language =  Language.fr.name
        result = self.manager.get_all_translations(source_text, from_language, to_language)
        self.assertTrue('Azure' in result)
        self.assertTrue('Google' in result)
        self.assertTrue('Watson' in result)
        self.assertTrue(result['Azure'] == 'Le coût est faible' or result['Azure'] == 'Le coût est très faible')
        self.assertEqual(result['Google'], 'À bas prix')
        self.assertEqual(result['Watson'], 'Le coût est très bas.')

    def test_transliteration(self):
        # pytest test_translation.py -k test_transliteration
        
        # chinese
        source_text = '成本很低'
        from_language = Language.zh_cn.name
        service = 'Azure'
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('chéng běn hěn dī', result)

        # thai
        source_text = 'ประเทศไทย'
        from_language = Language.th.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language]
        self.assertTrue(len(transliteration_candidates) == 2)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('prathetthai', result)


    def test_transliteration_easypronunciation(self):
        # pytest test_translation.py -rPP -k test_transliteration_easypronunciation

        # easypronunciation IPA test
        test_easy_pronunciation = True
        if not test_easy_pronunciation:
            return

        service = cloudlanguagetools.constants.Service.EasyPronunciation.name

        # french
        source_text = 'l’herbe est plus verte ailleurs'
        from_language = Language.fr.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('lɛʁb‿ ɛ ply vɛʁt‿ ajœʁ', result)

        # english
        source_text = 'do you have a boyfriend'
        from_language = Language.en.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('ˈduː ˈjuː ˈhæv ə ˈbɔɪˌfɹɛnd', result)        

        # italian
        source_text = 'Piacere di conoscerla.'
        from_language = Language.it.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('pjatʃere di konoʃʃerla', result)

        # japanese - Kana
        source_text = 'おはようございます'
        from_language = Language.ja.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service and 'Kana' in x['transliteration_name']]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('おはよー ございます', result)

        # japanese - romaji
        source_text = 'おはようございます'
        from_language = Language.ja.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service and 'Romaji' in x['transliteration_name']]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('ohayo– gozaimasu', result)

        # portuguese - portugal
        source_text = 'Posso olhar a cozinha?'
        from_language = Language.pt_pt.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('pˈɔsu oʎˈaɾ ɐ kuzˈiɲɐ', result)

        # portuguese - brazil
        source_text = 'Perdi a minha carteira.'
        from_language = Language.pt_br.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('peʁdʒˈi a mˈiɲɐ kaʁtˈejɾɐ', result)

        # spanish
        source_text = '¿A qué hora usted cierra?'
        from_language = Language.es.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language and x['service'] == service]
        self.assertTrue(len(transliteration_candidates) == 1)
        transliteration_option = transliteration_candidates[0]
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual('a ˈke ˈoɾa u̯sˈtɛð ˈsjɛra', result)


    def verify_transliteration(self, source_text, transliteration_option, expected_output):
        service = transliteration_option['service']
        transliteration_key = transliteration_option['transliteration_key']
        result = self.manager.get_transliteration(source_text, service, transliteration_key)
        self.assertEqual(expected_output, result)        


    def verify_transliteration_single_option(self, from_language, source_text, service, expected_result):
        from_language_name = from_language.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language_name and x['service'] == service]
        self.assertEqual(len(transliteration_candidates), 1)
        transliteration_option = transliteration_candidates[0]
        self.verify_transliteration(source_text, transliteration_option, expected_result)


    def verify_transliteration_multiple_options(self, from_language, source_text, service, expected_result_list):
        from_language_name = from_language.name
        transliteration_candidates = [x for x in self.transliteration_language_list if x['language_code'] == from_language_name and x['service'] == service]

        actual_result_list = []
        for transliteration_option in transliteration_candidates:
            transliteration_key = transliteration_option['transliteration_key']
            result = self.manager.get_transliteration(source_text, service, transliteration_key)
            actual_result_list.append(result)

        # sort both actual and expected
        actual_result_list.sort()
        expected_result_list.sort()

        self.assertEqual(actual_result_list, expected_result_list)


    def test_transliteration_epitran(self):
        # pytest test_translation.py -rPP -k test_transliteration_epitran

        service = cloudlanguagetools.constants.Service.Epitran.name

        # french
        self.verify_transliteration_multiple_options(Language.fr, 'l’herbe est plus verte ailleurs', service, ['l’ɛrbə ɛst plys vɛrtə ajlœr', 'l’hɛrbɛ ɛst plys vɛrtɛ elœrs'])

        # english 
        self.verify_transliteration_single_option(Language.en, 'do you have a boyfriend', service, 'du ju hæv ə bojfɹɛnd')

        # german
        self.verify_transliteration_multiple_options(Language.de, 'Können Sie mir das auf der Karte zeigen?', 
            service, 
            ['kønnən siː mir das awf dər karte t͡sajeːɡən?',
            'kønən siː mir das auf dər kaəte t͡saieɡən?',
            'kønən siː miʁ das auf deʁ kaɐte t͡saieɡən?'])

        # spanish
        self.verify_transliteration_single_option(Language.es, '¿A qué hora usted cierra?', service, '¿a ke oɾa usted siera?')
