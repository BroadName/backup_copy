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

    def _send_request(self, http_method, uri_path, params=None, headers=None, json=None, response_type=None):

        response = requests.request(http_method, f'{self.base_url}/{uri_path}', params=params, headers=headers, json=json)
        if response.status_code >= 400 and response.status_code != 409:
            raise HttpException(response.status_code, response.text)
        if response_type == json:
            response = response.json()
        return response


class YandexApi(ApiBasic):
    base_url = 'https://cloud-api.yandex.net/v1/disk'

    def __init__(self, access_token):
        self.token = access_token

    def create_folder(self):
        self._send_request(
            http_method='PUT',
            uri_path='resources',
            params={
                'path': 'photos'
            },
            headers={
                'Authorization': f'OAuth {self.token}'
            }
        )

    def upload_photos(self, name, url):
        self._send_request(
            http_method='POST',
            uri_path='resources/upload',
            params={
                'path': f'photos/{name}.jpg',
                'url': url
            },
            headers={
                'Authorization': f'OAuth {self.token}'
            }
        )


class VK(ApiBasic):

    base_url = 'https://api.vk.com/method/'
    yandex_base_url = 'https://cloud-api.yandex.net/'

    def __init__(self, access_token, user_id, yandex_token, version='5.199'):
        self.token = access_token
        self.y_token = yandex_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def users_info(self):
        return self._send_request(
            http_method='GET',
            uri_path='users.get',
            params={
                'user_ids': self.id,
                **self.params
            }
        )

    def photo_get(self, count=5):
        response = self._send_request(
            http_method='GET',
            uri_path='photos.get',
            params={
                'owner_id': self.id,
                'album_id': 'profile',
                'rev': '1',
                'extended': '1',
                'photo_sizes': True,
                'count': count,
                'v': self.version,
                **self.params
            },
            response_type='json'
        )

        list_urls = []
        check_names = []
        today = f'({str(date.today())})'

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

        # Create a folder in yandex disk's service through YandexApi class
        s = YandexApi(ya_token)
        s.create_folder()

        # uploading files
        for file in tqdm(list_urls, desc='Uploading photos'):
            s.upload_photos(file[0], file[1])
            time.sleep(0.01)
        return photos_info


config = configparser.ConfigParser()
config.read('config.ini')
vk_token = config['vk']['token']
u_id = config['vk']['user_id']
ya_token = config['yandex']['token']

vk = VK(vk_token, u_id, ya_token)
print(vk.photo_get())
