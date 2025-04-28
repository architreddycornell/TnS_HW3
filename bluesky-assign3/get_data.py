import os
import csv

from atproto import Client
from dotenv import load_dotenv

from pylabel import post_from_url

load_dotenv(override=True)
USERNAME = os.getenv("USERNAME")
PW = os.getenv("PW")


def has_scam_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ['money', 'guaranteed', 'returns', 'click', 'send', 'eth', 'crypto', 'bitcoin', 'giveaway', 'double', 'x2', 'limited', 'offer', 'away'])

def reply_post(post) -> bool:
    return getattr(post.post, 'reply', None) is not None

def quote_post(post) -> bool:
    embed = getattr(post.post.record, 'embed', None)
    return bool(embed and hasattr(embed, 'record'))

def has_mentions(post) -> bool:
    facets = getattr(post.post.record, 'facets', None)
    if facets:
        for f in facets:
            if f.features and any(getattr(feat, '$type', '').endswith('mention') for feat in f.features):
                return True
    return False


def main():
    client = Client()
    client.login(USERNAME, PW)
    posts = []
    matched_posts = []
    legit_posts = []
    list_of_accounts=[
        'trader-fazal.bsky.social', 
        'hivefortune.bsky.social', 
        'flipperflp.bsky.social', 
        'piiunivers.bsky.social', 
        'bsky.app',
        'technews.bsky.social',
        'someuser.bsky.social'
    ]
    cursor = None

    for account in list_of_accounts:
        print(f"\n Fetching from: {account}")
        cursor = None
        while True:
            try:
                response = client.app.bsky.feed.get_author_feed(
                    {'actor': account, 'cursor': cursor} if cursor else {'actor': account}
                )
            except Exception as e:
                print(f"❌ Failed to fetch from {account}\n{e}")
                break

            posts = response.feed
            cursor = getattr(response, 'cursor', None)
            if not posts:
                break

            for post in posts:
                record = getattr(post.post, 'record', None)
                text = getattr(record, 'text', '')
                labels = getattr(post.post, 'labels', [])
                label_vals = [label.val for label in labels]

                is_scam = (
                    has_scam_keywords(text) or
                    any(lbl in label_vals for lbl in ['!spam', '!scam']) or
                    reply_post(post) or 
                    quote_post(post) or 
                    has_mentions(post)
                )

                if is_scam:
                    matched_posts.append((
                        post.post.uri,
                        account,
                        1,
                        text
                    ))
                else:
                    legit_posts.append((
                        post.post.uri,
                        account,
                        0,
                        text
                    ))

                # if has_scam_keywords(text) or any(lbl in label_vals for lbl in ['!spam', '!scam']) \
                #    or reply_post(post) or quote_post(post) or has_mentions(post):
                #     matched_posts.append((
                #         post.post.uri,
                #         account,
                #         ','.join(label_vals),
                #         text
                #     ))

            if not cursor:
                break

    
    print(f"\n  {len(matched_posts)} scam posts.")


# Exporting
    os.makedirs('training-data', exist_ok=True)
    output_file = 'training-data/posts.csv'
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['URI', 'Account', 'Label', 'Post'])  # <-- updated column name
        for uri, account, label, text in matched_posts + legit_posts:
            writer.writerow([uri, account, label, text])

    print(f"Exported {len(matched_posts) + len(legit_posts)} posts to {output_file}")

if __name__ == "__main__":
    main()