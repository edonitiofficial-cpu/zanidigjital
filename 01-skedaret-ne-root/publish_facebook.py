"""Called by CI only after the website commit has been pushed successfully."""
import json
import os
import time
import urllib.parse
import urllib.request
from news_utils import facebook_queue_path, load_news_file


def main():
    token = os.environ.get('FACEBOOK_PAGE_TOKEN')
    if not token:
        print('Facebook: mungon token-i; publikimi u anashkalua.')
        return
    queue = load_news_file(facebook_queue_path())
    for post in queue:
        # Wait until the specific static page is available, rather than a fixed delay.
        for attempt in range(12):
            try:
                with urllib.request.urlopen(post['linku'], timeout=15) as response:
                    if response.status == 200:
                        break
            except Exception:
                pass
            time.sleep(15)
        else:
            raise RuntimeError('Artikulli ende nuk është online; Facebook nuk u publikua.')
        data = urllib.parse.urlencode({'message': post['mesazhi'], 'link': post['linku'], 'access_token': token}).encode()
        # Do not log requests, tokens or full exception responses containing credentials.
        try:
            with urllib.request.urlopen(urllib.request.Request('https://graph.facebook.com/v19.0/me/feed', data=data), timeout=30) as response:
                result = json.load(response)
            if not result.get('id'):
                raise RuntimeError('Facebook nuk ktheu ID publikimi.')
            print(f"Facebook: u publikua {post['linku']}")
        except Exception:
            raise RuntimeError('Publikimi në Facebook dështoi; kontrollo token-in dhe konfigurimin.') from None


if __name__ == '__main__':
    main()
