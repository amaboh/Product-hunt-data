from scrapy import Spider, Request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from ..items import ProductItem
import time

class WeeklySpider(Spider):
    name = 'weekly'
    allowed_domains = ['producthunt.com']

    def __init__(self):
        super().__init__()
        self.start_year = 2013
        self.end_year = 2024
        self.current_week = 49
        options = Options()
        options.add_argument('--headless') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(30)

    def start_requests(self):
        for year in range(self.end_year, self.start_year - 1, -1):
            max_week = self.current_week if year == self.end_year else 52
            for week in range(max_week, 0, -1):
                url = f'https://www.producthunt.com/leaderboard/weekly/{year}/{week}'
                yield Request(url=url, callback=self.parse_weekly, meta={'year': year, 'week': week}, dont_filter=True, errback=self.handle_error)

    def handle_error(self, failure):
        year = failure.request.meta.get('year')
        week = failure.request.meta.get('week')
        self.logger.error(f'Request failed for year {year} week {week}: {failure.value}')

    def wait_for_page_load(self, timeout=30):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(3)
            # Attempt infinite scroll to load all products
            max_scroll_attempts = 5
            prev_height = None
            for _ in range(max_scroll_attempts):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == prev_height:
                    break
                prev_height = new_height
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            return True
        except:
            self.logger.error("Error waiting for page load.")
            return False

    def parse_weekly(self, response):
        year = response.meta['year']
        week = response.meta['week']
        self.logger.info(f"Processing page for year {year} week {week}")

        try:
            self.driver.get(response.url)
            if not self.wait_for_page_load():
                self.logger.error(f"Page failed to load for year {year} week {week}")
                return

            products = []
            max_attempts = 3
            attempt = 0

            while attempt < max_attempts:
                try:
                    timeout = 15 * (attempt + 1)
                    products = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'section[data-test^="post-item-"]'))
                    )
                    if products:
                        break
                except TimeoutException:
                    attempt += 1
                    self.logger.warning(f"Attempt {attempt} failed to find products")
                    if attempt == max_attempts:
                        self.logger.error("Timeout waiting for products")
                        return
                    time.sleep(8)

            self.logger.info(f"Found {len(products)} products for year {year} week {week}")

            for idx, product in enumerate(products, 1):
                try:
                    # Extract product name
                    name_elem = product.find_element(By.CSS_SELECTOR, 'a[data-test^="post-name-"]')
                    name = name_elem.text.strip()

                    # Extract tagline
                    tagline_elem = product.find_element(By.CSS_SELECTOR, 'a.text-16.font-normal.text-dark-gray.text-gray-700')
                    tagline = tagline_elem.text.strip()

                    # Extract tags
                    try:
                        tag_container = product.find_element(By.CSS_SELECTOR, 'div[data-sentry-component="TagList"]')
                        tags = [t.text.strip() for t in tag_container.find_elements(By.TAG_NAME, 'a')]
                    except NoSuchElementException:
                        tags = []

                    # Extract comments count 
                    # The first button after tags that does not have data-test="vote-button"
                    # has the comments count.
                    comment_btn = product.find_element(
                        By.XPATH, 
                        './/button[not(@data-test="vote-button")]//div[contains(@class,"text-14 font-semibold")]'
                    )
                    comments = comment_btn.text.strip()

                    # Extract upvotes
                    upvote_btn = product.find_element(
                        By.XPATH, 
                        './/button[@data-test="vote-button"]//div[contains(@class,"text-14 font-semibold")]'
                    )
                    upvotes = upvote_btn.text.strip()

                    # Extract product URL
                    product_link = name_elem.get_attribute('href')

                    item = ProductItem()
                    item['name'] = name
                    item['tagline'] = tagline
                    item['upvotes'] = upvotes
                    item['comment_count'] = comments
                    item['tags'] = tags
                    item['week'] = week
                    item['year'] = year
                    item['product_url'] = product_link

                    # If you wish to extract comments details from product's page:
                    original_window = self.driver.current_window_handle
                    self.driver.execute_script("window.open('');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    try:
                        self.driver.get(product_link)
                        if self.wait_for_page_load():
                            # implement extract_comments if needed
                            # item['comments_list'] = self.extract_comments()
                            # If you don't need full comments detail, skip this part.
                            item['comments_list'] = []
                        else:
                            item['comments_list'] = []
                    finally:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)

                    yield item

                except Exception as e:
                    self.logger.error(f"Error processing product {idx}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error processing page for year {year} week {week}: {str(e)}")

    def extract_comments(self):
        comments = []
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="comment"]'))
            )

            scroll_attempts = 0
            max_scroll_attempts = 10

            while scroll_attempts < max_scroll_attempts:
                comment_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-test="comment"]')
                for comment in comment_elements:
                    try:
                        text = comment.find_element(By.CSS_SELECTOR, 'div[class*="text-16 font-normal"]').text.strip()
                        author = comment.find_element(By.CSS_SELECTOR, 'a[class*="text-14 font-semibold"]').text.strip()
                        date = comment.find_element(By.CSS_SELECTOR, 'time').get_attribute('datetime').strip()
                        up_str = comment.find_element(By.CSS_SELECTOR, 'div[data-test="comment-upvote-info"]').text.strip()
                        comment_data = {
                            'text': text,
                            'author': author,
                            'date': date,
                            'upvotes': up_str
                        }
                        if comment_data not in comments:
                            comments.append(comment_data)
                    except NoSuchElementException:
                        continue

                # Attempt to load more comments if button is present
                try:
                    load_more = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'button[class*="styles_button__BmLM4 styles_secondary__zB2Yb"]'))
                    )
                    if not load_more.is_displayed():
                        break
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                    time.sleep(1)
                    load_more.click()
                    time.sleep(2)
                    scroll_attempts += 1
                except (NoSuchElementException, TimeoutException):
                    break

        except Exception as e:
            self.logger.error(f"Error extracting comments: {e}")

        return comments

    def closed(self, reason):
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info("Chrome driver closed")