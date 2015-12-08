from urllib import parse

import requests
from requests.auth import HTTPBasicAuth

# Bing API key
API_KEY = "54wd7aqSGDrksbimHQxhVW5OoBa+1WGPANXy6kr1ta8"


def imageSearch(query, top=10):
    """Returns the decoded json response content

    :param query: query for search
    :param top: number of search result
    """
    # set search url
    query = '%27' + parse.quote_plus(query) + '%27'
    # web result only base url
    base_url = 'https://api.datamarket.azure.com/Bing/Search/v1/Image'
    url = base_url + '?Query=' + query + '&$top=' + str(top) + '&$format=json&ImageFilters=%27Aspect%3ASquare%27'

    # create credential for authentication
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.73 Safari/537.36"
    # create auth object
    auth = HTTPBasicAuth("", API_KEY)
    # set headers
    headers = {'User-Agent': user_agent}

    # get response from search url
    response_data = requests.get(url, headers=headers, auth=auth)
    # decode json response content
    json_result = response_data.json()

    return json_result['d']['results']
