import requests
import configparser
import json
from datetime import date
import time
from tqdm import tqdm


class HttpException(Exception):

    """Exception class, raise it, when API returns an error"""

    def __init__(self, status, message=''):
        self.status = status
        self.message = message

    def __str__(self):
        return f'http error: {self.status}\n{self.message}'


class ApiBasic:

    base_url = ''

    def _send_request(self, http_method, uri_path, params=None, json=None, response_type=None):

        response = requests.request(http_method, f'{self.base_url}/{uri_path}', params=params, json=json)
        if response.status_code >= 400:
            raise HttpException(response.status_code, response.text)
        if response_type == json:
            response = response.json()
        return response


class VK:

    base_url = 'https://api.vk.com/method/'
    yandex_base_url = 'https://cloud-api.yandex.net/'

    def __init__(self, access_token, user_id, yandex_token, version='5.199'):
        self.token = access_token
        self.y_token = yandex_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def users_info(self):
        params = {'user_ids': self.id}
        response = requests.get(self.base_url + 'users.get', params={**self.params, **params})
        return response.json()

    def create_folder(self):
        url_create_folder = f'{self.yandex_base_url}v1/disk/resources'
        params = {
            'path': 'photos'
        }
        headers = {
            'Authorization': f'OAuth {self.y_token}'
        }
        response = requests.put(url_create_folder, params=params, headers=headers)
        if response.status_code != 201:
            return f'Yandex: {response.status_code}'

    def upload_photos(self, name, url):
        url_upload = f'{self.yandex_base_url}v1/disk/resources/upload'
        params = {
            'path': f'photos/{name}.jpg',
            'url': url
        }
        headers = {
            'Authorization': f'OAuth {self.y_token}'
        }
        response = requests.post(url_upload, params=params, headers=headers)

    def photo_get(self, count=5):
        params = {
            'owner_id': self.id,
            'album_id': 'profile',
            'rev': '1',
            'extended': '1',
            'photo_sizes': True,
            'count': count,
            'v': self.version
        }
        response = requests.get(self.base_url + 'photos.get', params={**self.params, **params})
        if response.status_code >= 400:
            raise HttpException(response.status_code, response.text)

        list_urls = []
        check_names = []
        today = f'({str(date.today())})'

        print('Success')
        for list_params in tqdm(response.json()['response']['items'], desc='Get names and urls'):
            if list_params['likes']['count'] in check_names:
                list_urls.append([str(list_params['likes']['count']) + today,
                                  list_params.get('sizes', '')[-1]['url'],
                                  list_params.get('sizes', '')[-1]['type']])
            else:
                list_urls.append([list_params['likes']['count'],
                                  list_params.get('sizes', '')[-1]['url'],
                                  list_params.get('sizes', '')[-1]['type']])
                check_names.append(list_params['likes']['count'])
            time.sleep(0.075)

        # contain info about all photos
        photos_info = [{'file_name': '', 'size': ''} for _ in range(len(list_urls))]
        for i, elem in enumerate(tqdm(photos_info, desc='Make a json file')):
            elem['file_name'] = list_urls[i][0]
            elem['size'] = list_urls[i][-1]
            time.sleep(0.2)

        # create a file that will have info about all photos
        with open('photos_info.json', 'w', encoding='utf-8') as j:
            json.dump(photos_info, j)

        # Create a folder in yandex disk's service
        self.create_folder()

        # uploading files
        for file in tqdm(list_urls, desc='Uploading photos'):
            self.upload_photos(file[0], file[1])
            time.sleep(0.01)
        return photos_info


class YandexApi(ApiBasic):
    base_url = 'https://cloud-api.yandex.net/v1/disk'


config = configparser.ConfigParser()
config.read('config.ini')
vk_token = config['vk']['token']
u_id = config['vk']['user_id']
ya_token = config['yandex']['token']

vk = VK(vk_token, u_id, ya_token)
print(vk.photo_get())
