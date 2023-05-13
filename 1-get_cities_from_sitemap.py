"""The sitemap file contains only a single strings with all websites inside.
We will just get them with a beautiful regex

WARN : This does not work, the sitemap is not properly updated
"""

import json
import re


WEBSITE_PATTERN = re.compile(r"https:\/\/www.bien-dans-ma-ville.fr\/(.*?)\/")

def main():
    with open("data/sitemap-ville.xml", "r", encoding="utf-8") as file:
        sitemap_str = file.read()
        
    matches = WEBSITE_PATTERN.finditer(sitemap_str)
    websites = [m.group() for m in matches]
    
    print(len(websites))
    
    # with open("websites.json", "w", encoding="utf-8") as file:
    #     json.dump(websites, file)

if __name__ == "__main__":
    main()