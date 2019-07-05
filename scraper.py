from requests_html import HTMLSession
import math
import re
import time
from datetime import datetime
from multiprocessing import Pool, Manager

BASE_URL = 'http://ocremix.org'
pages_url_dict = {
    'systems': '/systems',  # The missing forward slash is how the site has it setup
    'games': '/games/',
    'remixes': '/remixes',
    'albums': '/albums/?&offset=0&sort=nameasc',
    'artists': '/artists/'
}
session = HTMLSession()
# manager = Manager()
# remix_dict = manager.dict()
# remix_dict = {}
remix_count = 0
game_count = 0


def get_request_count():
    systems_dict = scrape_systems_to_dict()
    total_request_count = 0

    for system in systems_dict.items():
        request_count = math.ceil(int(system[1]['remix_count']) / 30)
        total_request_count += request_count

    print(f'Total number of requests to scrape all systems: {total_request_count}')


def scrape_systems_to_dict():
    r = session.get(BASE_URL + pages_url_dict['systems'])

    system_table_body = r.html.find('table.data > tbody')[0]
    content = system_table_body.find('td')

    system_dict = {}
    remix_column_counter = 0

    for td in content:
        if 'align' in td.attrs and 'valign' in td.attrs:
            continue
        if 'valign' in td.attrs:
            system_name = td.text.split('\n')[1]
            system_dict[system_name] = {'link': None, 'remix_count': None}
            a_tag = td.find('a')[1]
            system_dict[system_name]['link'] = next(iter(a_tag.absolute_links))
        if 'align' in td.attrs:
            remix_column_counter += 1

            # Even numbered column contains the remix count
            if remix_column_counter % 2 == 0:
                if td.text != '0':
                    system_dict[system_name]['remix_count'] = td.text
                else:
                    # No need to keep a system with no remixes
                    del system_dict[system_name]

    return system_dict


def generate_complete_url_list(system_dict):
    all_urls = []
    for k, v in system_dict.items():
        remix_count = int(v['remix_count'])
        all_urls.append(''.join([v['link'], pages_url_dict['remixes']]))
        if remix_count > 30:
            # URL parameter for result offset
            offset = 0
            for x in range(math.floor(remix_count / 30)):
                offset += 30
                all_urls.append(f'{v["link"]}/remixes?&offset={offset}')

    return all_urls


def scrape_system_remixes_to_dict(remix_dict, url):
    page = session.get(url)
    remix_table_body = page.html.find(r'#main-content > div:nth-child(1) > div > div:nth-child(2) >'
                                      r' section > div > table > tbody', first=True)
    content = remix_table_body.find('tr')
    for tr in content:
        # grab image, game title, and composer(s)
        if 'class' not in tr.attrs:
            a_tags = tr.find('a')
            # grab game title
            game_name = a_tags[1].text.strip()
            # logic for skipping to next for loop iteration if the game has been scraped before
            if game_name in remix_dict:
                continue
            else:
                global game_count
                game_count += 1
                print(game_name)
            # grab image url
            img_tag = a_tags[0].find('img', first=True)
            # modifies url to point to larger image for "album" artwork collection
            img_url = BASE_URL + img_tag.attrs['src'].replace('thumbs/150', 'img-size/500')
            # grab composer(s)
            if len(a_tags) == 3:
                composers = a_tags[2].text.strip()
            else:
                composers = ', '.join([composer.text.strip() for composer in a_tags[2:]])
            # grab game title image
            img_request = session.get(BASE_URL + img_tag.attrs['src'].replace(r'thumbs/150', 'img-size/500'))
            if img_request.status_code == 200:
                # formats the game name, inserts the system, and users proper file extension for image
                game_name_reg = r"[\s|\.|\*|\/|(\:\s)]+"
                file_name = f'images/{re.sub(game_name_reg, "-", game_name).lower()}-{url.split("/")[-2]}' \
                            f'-title.{img_url.split(".")[-1]}'
                file_name = file_name.replace('"', '')
                with open(file_name, 'wb') as f:
                    f.write(img_request.content)
            remix_dict[game_name] = {
                # Accounts for those games without composers
                'composers': composers if composers else 'Unknown',
                'image': file_name
            }
        else:
            global remix_count
            remix_count += 1
            td_tags = tr.find('td')
            # grab remix name
            a_tags = td_tags[0].find('a')
            remix = a_tags[0].text[1:-1]
            # grab YouTube link
            yt_link = a_tags[0].attrs['data-preview']
            # grab songs_arranged
            songs_arranged = [a.text for a in a_tags[1:]]
            # grab remixers
            remixers = [a.text for a in td_tags[1].find('a')]
            # grab posted date
            month_date = td_tags[2].text.replace('\n', '')
            # year = td_tags[2].find('span', first=True).text
            posted_date = datetime.strptime(month_date, '%b %d%Y').date()
            # The below dance of dictionaries is due to the following excerpt from documentation:
            # Modifications to mutable values or items in dict and list proxies will not be propagated
            # through the manager, because the proxy has no way of knowing when its values or items are modified.
            # To modify such an item, you can re-assign the modified object to the container proxy
            # Without this, the individual remix dictionaries is not persisted in the containing remix_dict
            d = remix_dict[game_name]
            d[remix] = {
                'yt_link': yt_link,
                'songs_arranged': songs_arranged,
                'remixers': remixers,
                'posted_date': posted_date.strftime('%Y-%m-%d')
            }
            remix_dict[game_name] = d


def main():
    before = time.time()
    system_dict = scrape_systems_to_dict()
    all_urls = generate_complete_url_list(system_dict)
    with Manager() as manager:
        remix_dict = manager.dict()
        p = Pool(10)
        for url in all_urls:
            p.apply_async(scrape_system_remixes_to_dict, args=(remix_dict, url))
        p.close()
        p.join()
        after = time.time()
        import json
        print(json.dumps(dict(remix_dict), indent=4))
        print(f'Total # of Games: {game_count}\nTotal # of Remixes: {remix_count}')
        print(f'Execution time: {str(after - before)}')


if __name__ == '__main__':
    main()
