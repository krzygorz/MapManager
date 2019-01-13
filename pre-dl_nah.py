from urllib.request import urlopen
from bs4 import BeautifulSoup

def valid_entry(x): #oh man i miss haskell and pattern matching
    tds = x.find_all('td')
    return x.name == 'tr' and tds and len(tds) == 5 and tds[0].find('img',alt="[   ]",src="/icons/unknown.gif") and tds[1].a
def parse_entry(e):
    tds = e.find_all('td')
    name = tds[1].string
    date = tds[2].string
    size = tds[3].string
    return (name,date,size)

url = "http://142.44.142.152/fastdl/garrysmod/maps/?C=M;O=D;F=2"
data = urlopen(url)
s = BeautifulSoup(data, 'html.parser')
entries = s.table.find_all(valid_entry, recursive=False)
sorted_entries = sorted(map(parse_entry, entries), key=lambda x: x[1])