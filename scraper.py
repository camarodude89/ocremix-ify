from requests_html import HTMLSession
import math
import re
from datetime import datetime
from multiprocessing import pool, Manager

BASE_URL = 'http://ocremix.org'
pages_url_dict = {
    'systems': '/systems',  # The missing forward slash is how the site has it setup
    'games': '/games/',
    'remixes': '/remixes/',
    'albums': '/albums/?&offset=0&sort=nameasc',
    'artists': '/artists/'
}
session = HTMLSession()
# manager = Manager()
# remix_dict = manager.dict()
remix_dict = {}


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

    # total_remix_count = 0
    # for system in system_dict.items():
    #     print(f'{system[0]} --- Remixes: {system[1]["remix_count"]} --- Link: {system[1]["link"]}')
    #     total_remix_count += int(system[1]['remix_count'])
    #
    # print(f'\nTotal number of systems: {len(system_dict.keys())}')
    # print(f'Total number of remixes: {total_remix_count}')

    return system_dict


def generate_complete_url_list():
    pass


def scrape_system_remixes_to_dict(system_url):
    url_list = [f'{system_url}/remixes']
    r = session.get(url_list[0])

    # Grabs the total number of remix results for the system
    try:
        result_count = int(r.html.find(
            r'#main-content > div:nth-child(1) > div > div:nth-child(2) > section > div > nav:nth-child(1) >'
            r' ul > li:nth-child(1) > a',
            first=True).text.split()[-1])
    # This will be thrown if there is no result count due to all results fitting on one page.
    except AttributeError:
        result_count = 1

    # URL parameter for result offset
    offset = 0
    for x in range(math.floor(result_count / 30)):
        offset += 30
        url_list.append(f'{system_url}/remixes?&offset={offset}')

    for url in url_list:
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
                    file_name = f'images/{re.sub(game_name_reg, "-", game_name).lower()}-{system_url.split("/")[-1]}' \
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
                # noinspection PyTypeChecker
                remix_dict[game_name][remix] = {
                    'yt_link': yt_link,
                    'songs_arranged': songs_arranged,
                    'remixers': remixers,
                    'posted_date': posted_date.strftime('%Y-%m-%d')
                }

    import json
    print(json.dumps(remix_dict, indent=4))


def main():
    system_dict = scrape_systems_to_dict()
    for k, v in system_dict.items():
        print(k)
        scrape_system_remixes_to_dict(system_dict[k]['link'])
    # get_request_count()


if __name__ == '__main__':
    main()
