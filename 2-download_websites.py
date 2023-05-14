"""Download all the "avis.html" pages by reading the website's sitemap

WARN : This does not contains all the cities available
"""

from argparse import ArgumentParser
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import List, Tuple
import requests
from tqdm import tqdm

@dataclass
class Arguments:
    output_path: Path

def fetch_arguments() -> Arguments:
    parser = ArgumentParser("download_websites")
    parser.add_argument("output_path")
    args = parser.parse_args()
    
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return Arguments(output_path)

def fetch_url_content(url: str) -> str:
    return requests.get(url).text

def fetch_websites() -> List[Tuple[str, str]]:
    """
    Returns:
        List[Tuple[str, str]]: List of tuples containing
            - The city name (key)
            - The url
    """
    with open("data/sitemap-villeavis.xml", "r", encoding="utf-8") as file:
        sitemap_str = file.read()
    
    # We have a long list of urls to split
    # We want to extract the city name from the list    
    website_pattern = re.compile(r"https:\/\/www.bien-dans-ma-ville.fr\/(.*?)\/avis.html")
    matches = website_pattern.finditer(sitemap_str)
    return [(m.group(1), m.group()) for m in matches]

def main():
    args = fetch_arguments()
    websites = fetch_websites()
    print(f"Got {len(websites)} websites")
    with tqdm(websites) as pbar:
        for name, url in pbar:
            pbar.set_description(f"Fetch url \"{url}\"")
            
            html_content = fetch_url_content(url)
            if len(html_content) == 0:
                raise RuntimeError(f"No html content found in url {url}")
            
            output_path = args.output_path / f"{name}.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as file:
                file.write(html_content)

if __name__ == "__main__":
    main()