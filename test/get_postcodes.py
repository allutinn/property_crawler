import requests


# Fetch finnish post codes
def fetch_post_codes():
    url = "https://raw.githubusercontent.com/theikkila/postinumerot/refs/heads/master/postcodes.json"
    response = requests.get(url)
    response.raise_for_status()  # will raise an exception for HTTP errors
    data = response.json()
    post_codes = []
    for item in data:
        post_codes.append(item['postcode'])
    post_codes.sort()
    return post_codes
