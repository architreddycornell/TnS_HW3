"""Implementation of automated moderator"""

from typing import List
from atproto import Client
import csv
import re
from urllib.parse import urlparse
import os

T_AND_S_LABEL = "t-and-s"
DOG_LABEL = "dog"
THRESH = 0.3

class AutomatedLabeler:
    """Automated labeler implementation"""

    def __init__(self, client: Client, input_dir):
        self.client = client

        self.input_dir = input_dir

        self.news_domain_map = {}

        news_path = os.path.join(self.input_dir,"news-domains.csv")

        with open(news_path,"r",encoding="utf-8") as f:

            reader = csv.DictReader(f)

            for row in reader:
                domain = row["Domain"].strip().lower()

                source_label = row["Source"].strip().lower()

                self.news_domain_map[domain] = source_label
   

    """
    Helper Function to retrieve Bluesky post from URL
    """
    def post_from_url(self, url: str):
    
        parts = url.split("/")
        rkey = parts[-1]
        handle = parts[-3]
        return self.client.get_post(rkey, handle)

    def moderate_post(self, url: str) -> List[str]:
        """
        Apply moderation to the post specified by the given url
        """

        #Milestone 3: cite your sources
        labels_found = set()
        #Use helper function to get post from link
        post = self.post_from_url(url)

        if not post:
            return []

        post_data = post.value

        if not post_data:

            return []


        text = post_data.text or ""

        facets = post_data.facets or []

        #Extract link URL from post
        link_urls = []
        # checking text for direct link


        text_w_link = re.findall(r'(https?://[^\s]+)', text, flags=re.IGNORECASE)

        for link in text_w_link: 

            link_urls.append(link.lower())
        
        #Parse domain of links, compare them with stored domains

        for link in link_urls:
            parsed = urlparse(link)
            domain_host = parsed.netloc.lower()

            if domain_host.startswith("www."):

                domain_host = domain_host[4:]

            if domain_host in self.news_domain_map:

                labels_found.add(self.news_domain_map[domain_host])



        return list(labels_found)