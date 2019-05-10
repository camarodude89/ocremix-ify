from requests_html import HTMLSession

BASE_URL = 'http://ocremix.org'
pages_url_dict = {
    'systems': '/systems',  # The missing forward slash is how the site has it setup
    'games': '/games/',
    'remixes': '/remixes/',
    'albums': '/albums/?&offset=0&sort=nameasc',
    'artists': '/artists/'
}
session = HTMLSession()


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

    # print(f'\nTotal number of systems: {len(system_dict.keys())}')
    # print(f'Total number of remixes: {total_remix_count}')

    return system_dict


def scrape_system_remixes_to_dict(system_url):
    r = session.get(f'{system_url}/remixes')

    page_selector = r.html.find('select', first=True)
    # the first option tag is skipped, it contains no URL
    options = page_selector.find('option')[1:]

    remix_dict = {}
    game_name_set = set()

    for option in options:
        page = session.get(BASE_URL + option.attrs['value'])
        jukebox_table_body = page.html.find('table', first=True)
        content = jukebox_table_body.find('td')
        for td in content:
            if 'valign' in td.attrs and 'colspan' in td.attrs:
                a_tag = td.find('a')
                game_name = a_tag[0].text.strip()
                if len(a_tag) == 2:
                    artists = a_tag[1].text.strip()
                else:
                    artists = ', '.join([artist.text.strip() for artist in a_tag[1:]])
                if game_name not in remix_dict:
                    remix_dict[game_name] = {
                        'artists': artists,
                        'remix': {
                            'yt_link': None,
                            'songs_arranged': None,
                            'remixers': None,
                            'posted_date': None
                        }
                    }

    game_name_list = list(game_name_set)
    game_name_list.sort()
    for game in game_name_list:
        print(game)


def main():
    system_dict = scrape_systems_to_dict()
    scrape_system_remixes_to_dict(system_dict['SNES']['link'])


if __name__ == '__main__':
    main()
