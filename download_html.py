import requests

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,*/*',
    'Accept-Language': 'az,ru;q=0.9',
})

targets = {
    'bina': 'https://bina.az/baki/kiraye/menziller?page=1',
    'tap': 'https://tap.az/elanlar',
    'arenda': 'https://arenda.az/'
}

for name, url in targets.items():
    res = s.get(url)
    res.encoding = res.apparent_encoding or 'utf-8'
    with open(f'{name}.html', 'w', encoding='utf-8') as f:
        f.write(res.text)
    print(f'Saved {name}.html')
