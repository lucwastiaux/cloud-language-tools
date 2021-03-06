import os
import logging
import requests
import urllib.parse
import xml.dom.minidom
import xml.etree.ElementTree
import pprint
import datetime
import secrets
import time

TRACKED_ITEM_CODE='thousand_chars'

class GetCheddarUtils():
    def __init__(self):
        self.product_code = secrets.config['getcheddar']['product_code']
        self.user = secrets.config['getcheddar']['user']
        self.api_key = secrets.config['getcheddar']['api_key']

    def get_api_secret(self):
        return self.api_key

    def decode_webhook(self, data):
        # self.print_json_webhook(data)
        activity_type = data['activityType']
        if activity_type == 'customerDeleted':
            return {
                'type': activity_type,
                'code': data['customer']['code']
            }
        overage_allowed = data['subscription']['plan']['items'][0]['overageAmount'] != '0.00' and activity_type != 'subscriptionCanceled'
        return {
            'type': activity_type,
            'code': data['customer']['code'],
            'email': data['customer']['email'],
            'thousand_char_quota': data['subscription']['plan']['items'][0]['quantityIncluded'],
            'thousand_char_overage_allowed': int(overage_allowed == True),
            'thousand_char_used': data['subscription']['invoice']['items'][0]['quantity']
        }


    def decode_customer_element(self, root):
        customer_code = root.attrib['code']
        customer_email = root.find('./email').text

        quantity_included = int(root.find('./subscriptions/subscription[1]/plans/plan[1]/items/item[@code="thousand_chars"]/quantityIncluded').text)
        overage_amount = float(root.find('./subscriptions/subscription[1]/plans/plan[1]/items/item[@code="thousand_chars"]/overageAmount').text)
        canceled_date = root.find('./subscriptions/subscription[1]/canceledDatetime').text
        overage_allowed = overage_amount > 0 and canceled_date == None
        current_usage = float(root.find('./subscriptions/subscription[1]/items/item[@code="thousand_chars"]/quantity').text)

        return {
            'code': customer_code,
            'email': customer_email,
            'thousand_char_quota': quantity_included,
            'thousand_char_overage_allowed': int(overage_allowed == True),
            'thousand_char_used': current_usage,
        }

    def decode_customer_xml(self, xml_str):
        root = xml.etree.ElementTree.fromstring(xml_str)
        customer_element = root.find('./customer')
        return self.decode_customer_element(customer_element)


    def print_json_webhook(self, data):
        webhook_formatted = pprint.pformat(data)
        f = open('getcheddar_webhook_data.py', 'w')
        f.write(webhook_formatted)
        f.close()        
        print(webhook_formatted)

    def print_xml_response(self, content):
        dom = xml.dom.minidom.parseString(content)
        pretty_xml_as_string = dom.toprettyxml(newl='')
        f = open('getcheddar_response.xml', 'w')
        f.write(pretty_xml_as_string)
        f.close()
        # print(pretty_xml_as_string)

    def report_customer_usage(self, customer_code, thousand_char_quantity):
        customer_code_encoded = urllib.parse.quote(customer_code)
        url = f'https://getcheddar.com/xml/customers/add-item-quantity/productCode/{self.product_code}/code/{customer_code_encoded}/itemCode/{TRACKED_ITEM_CODE}'
        # print(url)
        params = {'quantity': thousand_char_quantity}
        response = requests.post(url, auth=(self.user, self.api_key), data=params)
        if response.status_code == 200:
            # success
            return self.decode_customer_xml(response.content)
        else:
            error_message = f'Could not report customer usage: {response.content}'
            raise Exception(error_message)

    def get_customer(self, customer_code):
        # /customers/get/productCode/MY_self.product_code/code/MY_CUSTOMER_CODE
        customer_code_encoded = urllib.parse.quote(customer_code)
        url = f'https://getcheddar.com/xml/customers/get/productCode/{self.product_code}/code/{customer_code_encoded}'
        # print(url)
        response = requests.get(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            # success
            # self.print_xml_response(response.content)
            customer_data = self.decode_customer_xml(response.content)
            print(customer_data)
            return customer_data
        else:
            print(response.content)

    def get_all_customers(self):
        # /customers/get/productCode/MY_PRODUCT_CODE
        url = f'https://getcheddar.com/xml/customers/get/productCode/{self.product_code}'
        # print(url)
        logging.info(f'retrieving all getcheddar customer data')
        result = []
        response = requests.get(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            # success
            # self.print_xml_response(response.content)
            root = xml.etree.ElementTree.fromstring(response.content)
            customer_list = root.findall('./customer')
            for customer in customer_list:
                customer_data = self.decode_customer_element(customer)
                # print(customer_data)
                result.append(customer_data)
            # print(self.decode_customer_xml(response.content))
            return result
        else:
            error_message = f'could not get all customer data: {response.content}'
            raise Exception(error_message)



    # for testing purposes
    # ====================

    def ensure_dev(self):
        if self.product_code != 'LANGUAGE_TOOLS_DEV' and self.product_code != 'LANGUAGE_TOOLS_LOCAL':
            raise Exception('must be in dev environment !')


    def create_test_customer(self, code, email, first_name, last_name, plan):
        self.ensure_dev()

        url = f'https://getcheddar.com/xml/customers/new/productCode/{self.product_code}'
        params = {
            'code': code,
            'email': email,
            'firstName': first_name,
            'lastName': last_name,
            'subscription[planCode]': plan,
            'subscription[ccFirstName]': first_name,
            'subscription[ccLastName]': last_name,
            'subscription[ccNumber]': '370000000000002',
            'subscription[ccCardCode]': '1234',
            'subscription[ccExpiration]': '04/2025'
        }
        response = requests.post(url, auth=(self.user, self.api_key), data=params)
        if response.status_code == 200:
            # success
            # self.print_xml_response(response.content)
            print(self.decode_customer_xml(response.content))
            logging.info(f'created customer {code}')
        else:
            print(response.content)        

    def update_test_customer(self, code, plan):
        self.ensure_dev()

        customer_code_encoded = urllib.parse.quote(code)
        url = f'https://getcheddar.com/xml/customers/edit-subscription/productCode/{self.product_code}/code/{customer_code_encoded}'
        params = {
            'planCode': plan
        }
        response = requests.post(url, auth=(self.user, self.api_key), data=params)
        if response.status_code == 200:
            # success
            # self.print_xml_response(response.content)
            print(self.decode_customer_xml(response.content))
        else:
            print(response.content)            

    def cancel_test_customer(self, code):
        self.ensure_dev()

        customer_code_encoded = urllib.parse.quote(code)
        url = f'https://getcheddar.com/xml/customers/cancel/productCode/{self.product_code}/code/{customer_code_encoded}'
        response = requests.post(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            # success
            # self.print_xml_response(response.content)
            print(self.decode_customer_xml(response.content))
        else:
            print(response.content)            


    def delete_test_customer(self, code):
        self.ensure_dev()

        # /customers/delete/productCode/MY_self.product_code/code/MY_CUSTOMER_CODE
        customer_code_encoded = urllib.parse.quote(code)
        url = f'https://getcheddar.com/xml/customers/delete/productCode/{self.product_code}/code/{customer_code_encoded}'
        response = requests.post(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            # success
            logging.info(f'customer {code} deleted')
        else:
            print(response.content)                    

    def delete_all_test_customers(self):
        self.ensure_dev()

        logging.warning('WARNING DELETING ALL CUSTOMERS IN 30s')
        time.sleep(30)
        # /customers/delete-all/confirm/[current unix timestamp]/productCode/MY_PRODUCT_CODE
        timestamp = int(datetime.datetime.now().timestamp())
        url = f'https://getcheddar.com/xml/customers/delete-all/confirm/{timestamp}/productCode/{self.product_code}'
        response = requests.post(url, auth=(self.user, self.api_key))
        if response.status_code == 200:
            # success
            logging.info('all test customers deleted')
        else:
            print(response.content)                    


if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y%m%d-%H:%M:%S',
                        level=logging.INFO)

    cheddar_utils = GetCheddarUtils()
    customer_code = 'languagetools+customer5@mailc.net'
    # cheddar_utils.report_customer_usage(customer_code)
    # cheddar_utils.get_customer(customer_code)
    cheddar_utils.get_all_customers()