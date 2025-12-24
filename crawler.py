'''Web scrapper for Korean cosmetic online shop hollyshop.ru'''
import time
import json
import os

from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
import pandas as pd


class HollyshopCrawling:
    '''
    Crawler for hollyshop.ru that finds and extracts reviews.

    Attributes:
        url_hollyshop (str): Base URL for paginated product listings.
        max_hollyshop (int): Number of pages to iterate over when crawling.
        path (str): Base filename (without extension) for saving.
    '''
    def __init__(self):
        self.url_hollyshop = 'https://hollyshop.ru/catalog/basecare/?PAGEN_1='
        self.max_hollyshop = 100
        self.path = 'hollyshop_reviews'

    def save_links_to_json(self, links: list[str]):
        '''
        Save a list of product review links to a JSON file.

        Args:
            links (list[str]): List of product review URLs to save.
        '''
        if not os.path.exists('data'):
            os.mkdir('data')
        with open(f'data/{self.path}.json', 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=4)

    def save_reviews_to_csv(self, reviews: list[dict]):
        '''
        Save an iterable of review dictionaries to a CSV file.

        Args:
            reviews (list[dict] or pandas.DataFrame): Review records to save.
        '''
        df_reviews = pd.DataFrame(reviews)
        if not os.path.exists('data'):
            os.mkdir('data')
        df_reviews.to_csv(f'data/{self.path}.csv', index=False)

    def read_links_from_json(self) -> list[str]:
        '''
        Read product review links from the JSON file.

        Returns:
            list[str]: A list of product review URLs.

        Raises:
            FileExistsError: If the expected JSON file is missing.
        '''
        if os.path.exists(f'data/{self.path}.json'):
            with open(f'data/{self.path}.json', 'r', encoding='utf-8') as f:
                links = json.load(f)
            return links

        raise FileExistsError(f'File data/{self.path}.json is missing')

    def read_reviews_from_csv(self) -> pd.DataFrame:
        '''
        Read saved reviews from CSV.

        Returns:
            pandas.DataFrame: DataFrame containing saved reviews.

        Raises:
            FileExistsError: If the expected CSV file is missing.
        '''
        if os.path.exists(f'data/{self.path}.csv'):
            reviews = pd.read_csv(f'data/{self.path}.csv')
            return reviews
        raise FileExistsError(f'File data/{self.path}.csv is missing')

    def crawl_nth_page(self, html_code: str) -> str | None:
        '''
        Parse a page's HTML and return the first product link with reviews.

        Args:
            html_code (str): HTML source of a listing page.

        Returns:
            str or None: The reviews URL found on the page, or None.
        '''
        soup_n = BeautifulSoup(html_code)
        divs = soup_n.find_all('div', attrs={'class': 'catalog__list-item'})
        for div in divs:
            if div.find('div', attrs={'class': 'tag-rating'}):
                href = div.find('a').attrs['href']
                link = f'https://hollyshop.ru{href}reviews/'

                return link
        return None

    def crawl_n_pages(self):
        '''
        Crawl multiple listing pages and collect product review links.

        Iterates from page 1 to `self.max_hollyshop`, extracts the first
        rated product link from each page, saves results to JSON,
        and respects a short delay between requests.
        '''
        hollyshop_products = []

        for n in tqdm(range(1, self.max_hollyshop + 1)):
            hollyshop_n = requests.get(f'{self.url_hollyshop}{n}', timeout=10)
            hollyshop_n = hollyshop_n.content.decode('utf-8')
            link = self.crawl_nth_page(hollyshop_n)
            if link:
                hollyshop_products.append(link)
            time.sleep(5)

        self.save_links_to_json(hollyshop_products)

    def crawl_nth_review(self, html_code: str, link: str) -> list[dict] | None:
        '''
        Parse a product review page and extract individual review records.

        Args:
            html_code (str): HTML content of a product's review page.
            link (str): The URL of the review page being parsed.

        Returns:
            list[dict] or None: A list of review dictionaries with keys:
                - 'name' (str): Product name
                - 'category' (str): Product category
                - 'review' (str): Review text
                - 'emojis' (str): Emojis found as a space-separated string
                - 'rating' (int): Number of rating stars
                - 'url' (str): Source URL
            Returns None if the page does not contain name (empty).
        '''
        nth_reviews = []
        soup_n = BeautifulSoup(html_code)
        name = soup_n.find(
            'div',
            attrs={'class': 'reviews-page__product-card-name'}
            )
        if not name:
            return None

        name = name.text
        category = soup_n.find(
            'div',
            attrs={'class': 'reviews-page__product-card-category'}
            ).text
        divs = soup_n.find_all('div', attrs={'class': 'reviews__list-item'})

        for div in divs:
            text = div.find(
                'div',
                attrs={'class': 'reviews__list-item-body-content'}
                ).text
            rating = div.find(
                'div',
                attrs={'class': 'rating-stars'}
                )
            rating = len(rating.find_all('span'))
            emojis = div.find_all('img', attrs={'class': 'emo'})
            if emojis:
                emojis = [f':{emoji.attrs['alt']}:' for emoji in emojis]
            nth_reviews.append(
                {
                    'name': name,
                    'category': category,
                    'review': text.strip(),
                    'emojis': ' '.join(emojis),
                    'rating': rating,
                    'url': link
                }
            )
        return nth_reviews

    def crawl_n_reviews(self):
        '''
        Crawl all product review pages from saved links and aggregate reviews.

        Reads links from `{self.path}.json`, fetches and parses each page,
        accumulates review records, periodically persists a pickle file
        and finally saves a CSV.
        '''
        hollyshop_aggregated_reviews = []
        hollyshop_products = self.read_links_from_json()

        for url in tqdm(hollyshop_products):
            hollyshop_reviews = requests.get(url, timeout=10)
            hollyshop_reviews = hollyshop_reviews.content.decode('utf-8')
            url_reviews = self.crawl_nth_review(hollyshop_reviews, url)
            if url_reviews:
                hollyshop_aggregated_reviews.extend(url_reviews)

            hollyshop_df_reviews = pd.DataFrame(hollyshop_aggregated_reviews)
            hollyshop_df_reviews.to_pickle(f'{self.path}.pkl')
            time.sleep(1)

        self.save_reviews_to_csv(hollyshop_aggregated_reviews)
