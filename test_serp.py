import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.settings import get_settings
from serpapi import GoogleSearch
import json

def test():
    settings = get_settings()
    params = {
        "engine": "google",
        "q": "SBP",
        "tbm": "nws",
        "gl": "pk",
        "api_key": "b727c9b563a7e5668b3333b3b19f1919a44f971e880bd7ba61e548b89c953a51",
        "num": 2
    }
    
    search = GoogleSearch(params)
    results = search.get_dict()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test()
