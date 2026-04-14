import requests
from bs4 import BeautifulSoup

def parse_park(park):
    data = []
    soup = None
    try:
        # Gathering main park page
        url = f'https://rcdb.com/qs.htm?qs={park}'
        while True:  # Ensures search leads to park page
            response = requests.get(url, verify=True)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            h4 = soup.find_all('h4')
            if len(h4) > 0: #Checks if link redirects to a list of parks
                url = response.url
                break
            else:
                p = soup.find('p')
                try:
                    url = "https://rcdb.com" + p.find('a').get('href')
                except Exception:
                    return None
        
        park_official = soup.find('div', id='feature').find('h1').text
        data.append((park_official, "park", url))

        # Only looking at the first h4 (operating coasters) and following to page
        for i in range(len(h4)):
            if "Operating Roller Coasters: " in h4[i].text or "SBNO Roller Coasters: " in h4[i].text:
                url = "https://rcdb.com" + h4[i].find('a').get('href')
                response = requests.get(url, verify=True)
                response.raise_for_status()
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                ride_table = soup.find('div', class_='stdtbl rer').find('tbody').find_all('tr')
                for tr in ride_table:
                    ride = tr.find_all('td')[1].find('a')
                    if ride.text in "unknown":
                        continue
                    data.append((ride.text, "ride", "https://rcdb.com" + ride.get('href')))
        return data
    except Exception:
        # Purposely may reach here if h4[i].text causes exception, meaning there are not open coasters 
        # May be interrupted from above, so return partial reading at best
        return data if data else None
        
def main():
    park = input("Park: ") 
    results = parse_park(park)
    if results:
        for item in results:
            print(item)
    else:
        print("No park found")
   
if __name__ == '__main__':
    main()