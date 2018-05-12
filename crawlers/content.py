from pymongo import MongoClient
import requests
import time


class ContentDownloader:

    REQUEST_WAIT = 0.03
    DATABASE_NAME = 'gog'

    PRODUCT_COLLECTION_NAME = 'product'
    RANK_COLLECTION_NAME = 'rank'

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
        for item in self.item_ids:
            self.get_item(url_product.format(item), self.PRODUCT_COLLECTION_NAME)

    def get_item(self, url, collection_name):
        result = self._run_request(url)
        self._store_result_at_mongo(collection_name, result.json())
        return result

    def _store_result_at_mongo(self, collection_name, item):
        with MongoClient() as client:
            collection = client[self.DATABASE_NAME][collection_name]
            collection.insert_one(item)


if __name__ == '__main__':
    content_downloader = ContentDownloader()
    content_downloader.download()
