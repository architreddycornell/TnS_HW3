"Automated Labeler"


from __future__ import annotations
from typing import List, Set
from atproto import Client, models
from urllib.parse import urlparse
import csv, re, os, requests, imagehash, string
from PIL import Image
from io import BytesIO

T_AND_S_LABEL = "t-and-s"    
DOG_LABEL      = "dog"
THRESH         = 16          

class AutomatedLabeler:
    """Automated labeler implementation """

    def __init__(self, client: Client, input_dir: str):
        self.client     = client
        self.input_dir  = input_dir

        # Milestone 3 (cite your sources)
        self.news_domain_map = self._load_domain_map("news-domains.csv")

        #  Milestone 4 (dog image detector)
        dog_img_dir = os.path.join(input_dir, "dog-list-images")
        self.dog_hashes = self._load_dog_hashes(dog_img_dir)

        # Milestone 2

        self.ts_domains = self._load_simple_list("t-and-s-domains.csv","Domain")

        self.ts_words = self._load_simple_list("t-and-s-words.csv", "Word")

    # helper functions
    def _load_domain_map(self, csv_name: str) -> dict[str, str]:
        
        path = os.path.join(self.input_dir, csv_name)
        mapping: dict[str, str] = {}
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                mapping[row["Domain"].strip().lower()] = row["Source"].strip().lower()
        return mapping

    def _load_simple_list(self, fname: str, col: str) -> Set[str]:
        path = os.path.join(self.input_dir, fname)
        items: Set[str] = set()
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                
                dom = row[col].strip().lower()

                if dom.startswith("www."):

                    dom = dom[4:]

                dom = dom.rstrip("/")

                items.add(dom)
                
        return items

    def _load_dog_hashes(self, directory: str):
        #Compute perceptual hashes for every reference dog image
        hashes = []
        for fname in os.listdir(directory):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    im = Image.open(os.path.join(directory, fname)).convert("RGB").resize((256, 256))
                    hashes.append(imagehash.phash(im))
                except Exception as e:
                    print(f"[dog‑loader] could not hash {fname}: {e}")
        return hashes

    def _post_from_url(self, url: str):
        parts  = url.split("/")
        rkey   = parts[-1]
        handle = parts[-3]
        return self.client.get_post(rkey, handle)

    #Milestone 2 - T&S

    def _ts_labels(self,text:str) -> Set(str):

        text_lc = text.lower()

        tokens = {tok.strip(string.punctuation).lower() for tok in text_lc.split()}

        for term in self.ts_words:

            if " " in term or "&" in term:

                if term in text_lc:

                    return {T_AND_S_LABEL}
            
            elif term in tokens:

                return {T_AND_S_LABEL}

        for link in re.findall(r'https?://[^\s]+', text_lc, flags=re.I):

            domain = urlparse(link).netloc.lower()

            if domain.startswith("www."):

                domain = domain[4:]

            domain = domain.rstrip("/")

            if any(domain == d or domain.endswith("." + d) for d in self.ts_domains):

                return {T_AND_S_LABEL}
            
        return set()

    #  Milestone 3  – Cite
    def _cite_labels(self, text: str) -> Set[str]:

        labels: Set[str] = set()
        for link in re.findall(r'https?://[^\s]+', text, flags=re.I):
            host = urlparse(link.lower()).netloc
            if host.startswith("www."):
                host = host[4:]
            if host in self.news_domain_map:
                labels.add(self.news_domain_map[host])
        return labels

    #   Milestone 4  – Dogs
    def _extract_image_urls(self, post: models.AppBskyFeedDefs.FeedViewPost) -> List[str]:
        urls = []
        embed = getattr(post.record, "embed", None)
        if isinstance(embed, models.AppBskyEmbedImages.Main):
            for img in embed.images:
                did = post.author.did
                cid = img.image.ref.link
                urls.append(f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={did}&cid={cid}")
        return urls

    def _is_dog_image(self, url: str) -> bool:
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            im   = Image.open(BytesIO(resp.content)).convert("RGB").resize((256, 256))
            h    = imagehash.phash(im)
            return any((h - dh) <= THRESH for dh in self.dog_hashes)
        except Exception:
            return False

    def _dog_labels(self, web_post_url: str) -> Set[str]:
        """Return {'dog'} if attached image matches reference set."""
        labels: Set[str] = set()
        try:
            at_uri = self._web_to_at_uri(web_post_url)
            post   = self.client.app.bsky.feed.get_post_thread({"uri": at_uri}).thread.post
            for img_url in self._extract_image_urls(post):
                if self._is_dog_image(img_url):
                    labels.add(DOG_LABEL)
                    break
        except Exception as e:
            print(f"[dog‑checker] failed on {web_post_url}: {e}")
        return labels

    @staticmethod
    def _web_to_at_uri(url: str) -> str:
        parts = url.strip().split("/")
        handle, post_id = parts[4], parts[6]
        return f"at://{handle}/app.bsky.feed.post/{post_id}"

    def moderate_post(self, url: str) -> List[str]:
        """Return a list of labels that apply to the post (runs all checks)."""
        labels: Set[str] = set()

        #  milestone 2 (t&s) , 3 (cite) 

        resp = self._post_from_url(url)
        if resp and resp.value and resp.value.text:
            text = resp.value.text

            labels.update(self._ts_labels(text))

            labels.update(self._cite_labels(text))

        #milestone 4 - dogs
        if DOG_LABEL not in labels:                    
            labels.update(self._dog_labels(url))

        # ---------- milestone 2 (T&S) would slot in here ---------------------

        return list(labels)
