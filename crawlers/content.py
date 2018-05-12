from bs4 import BeautifulSoup
from pymongo import MongoClient
import requests
import time


class ContentDownloader:
    REQUEST_WAIT = 0.01
    DATABASE_NAME = 'gog'

    PRODUCT_COLLECTION_NAME = 'product'
    RANK_COLLECTION_NAME = 'rank'
    SERIES_COLLECTION_NAME = 'series'

    def __init__(self):
        self.item_ids = set()
        self.total_pages = 0

    def download(self):
        self.get_total_pages()
        self.get_item_ids()
        self.get_items_description()

    def get_total_pages(self):
        url = 'https://api.gog.com/v1/games'
        result = self._run_request(url)
        self.total_pages = result.json()['pages']

    def _run_request(self, url):
        result = requests.get(url)
        time.sleep(self.REQUEST_WAIT)
        return result

    def get_item_ids(self):
        url = 'https://api.gog.com/v1/games?page={}'
        for page in range(1, self.total_pages+1):
            result = self._run_request(url.format(page))
            self._load_products_from_page(result.json()['_embedded']['items'])

    def _load_products_from_page(self, products):
        for product in products:
            self.item_ids.add(product['_embedded']['product']['id'])

    def get_items_description(self):
        url_product = 'https://api.gog.com/v1/games/{}'
        for enum_id, item in enumerate(self.item_ids):
            if enum_id % 5 == 0:
                print(f'Prosessed {enum_id} items ~ {enum_id/2450.}%')

            result = self.get_item(url_product.format(item), self.PRODUCT_COLLECTION_NAME)

            try:
                url = result.json()['_links']['store']['href']
            except Exception as e:
                print(f'no store link {e}')
                continue

            self.get_product_card_data(url=url, item_id=item)

    def get_item(self, url, collection_name):
        result = self._run_request(url)
        self._store_result_at_mongo(collection_name, result.json())
        return result

    def get_product_card_data(self, url, item_id):
        page_result = self._run_request(url)

        try:
            self.get_total_rank(page_result, item_id)
        except Exception as e:
            print(e, 'soup problem')

        try:
            self.get_series(page_result, item_id)
        except Exception as e:
            print(e, 'soup problem')

    def get_total_rank(self, page_result, item_id):
        item = {
            'id': item_id
        }
        soup = BeautifulSoup(page_result.content, 'html.parser')
        item_class = soup.find('div', class_='average-rating')
        for metadata in item_class.find_all('meta'):
            if metadata.attrs['itemprop'] == 'ratingValue':
                item['ratingValue'] = metadata.attrs['content']
            if metadata.attrs['itemprop'] == 'ratingCount':
                item['ratingCount'] = metadata.attrs['content']

        self._store_result_at_mongo(self.RANK_COLLECTION_NAME, item)

    def get_series(self, page_result, item_id):
        item = {
            'id': item_id,
            'series': [],
        }
        soup = BeautifulSoup(page_result.content, 'html.parser')
        item_class = soup.find('div', class_='module--buy-series')

        if item_class is None:
            return

        for product in item_class.find_all('div', class_='product-state-holder'):
            if product.attrs['gog-product']:
                item['series'].append(product.attrs['gog-product'])

        if item['series']:
            self._store_result_at_mongo(self.SERIES_COLLECTION_NAME, item)

    def _store_result_at_mongo(self, collection_name, item):
        with MongoClient() as client:
            collection = client[self.DATABASE_NAME][collection_name]
            collection.insert_one(item)


if __name__ == '__main__':
    content_downloader = ContentDownloader()
    content_downloader.download()
