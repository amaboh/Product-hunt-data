from scrapy import Item, Field

class ProductItem(Item):
    name = Field()
    tagline = Field()
    tags = Field()
    upvotes = Field()
    comment_count = Field()
    comments = Field()
    week = Field()
    year = Field()
    product_url = Field()
    comments_list = Field()