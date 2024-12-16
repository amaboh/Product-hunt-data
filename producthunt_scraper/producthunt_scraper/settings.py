BOT_NAME = 'producthunt_scraper'
SPIDER_MODULES = ['producthunt_scraper.spiders']
NEWSPIDER_MODULE = 'producthunt_scraper.spiders'

# Core Settings
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS = 1  # Reduced to 1 since we're using Selenium directly
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Feed Export
FEED_EXPORT_ENCODING = 'utf-8'

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Additional Settings
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 180