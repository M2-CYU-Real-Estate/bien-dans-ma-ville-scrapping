"""Use all downloaded html pages in order to get all wanted data
"""

from argparse import ArgumentParser
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterator, List, Tuple
from bs4 import BeautifulSoup, Tag
import pandas as pd
from tqdm import tqdm

WEBSITE_ROOT = "https://www.bien-dans-ma-ville.fr"

# ==== ARGUMENT PARSING ====
@dataclass
class Arguments:
    input_folder_path: Path
    output_folder_path: Path

def fetch_arguments() -> Arguments:
    parser = ArgumentParser("Scrape websites")
    parser.add_argument("input_path", help="The folder containing all html files")
    parser.add_argument("output_path", help="The folder where generated content will go")
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    input_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return Arguments(input_path, output_path)

# ==== SCRAPPING FUNCTIONS ====

@dataclass
class Scores:
    security: float = -1.0
    education: float = -1.0
    hobbies: float = -1.0
    environment: float = -1.0
    practicality: float = -1.0
    
    def normalize(self, max: float = 5.0) -> "Scores":
        return Scores(self.security / max, 
                      self.education / max, 
                      self.hobbies / max, 
                      self.environment / max, 
                      self.practicality / max
        )
        
    def to_json(self):
        return {
            "security": self.security,
            "education": self.education,
            "hobbies": self.hobbies,
            "environment": self.environment,
            "practicality": self.practicality
            
        }
        
@dataclass
class NearbyCity:
    url: str
    name: str
    contains_scores: bool
    
    def to_json(self) -> dict:
        return {
            "url": self.url,
            "name": self.name,
            "contains_scores": self.contains_scores
        }
    
@dataclass
class CityInformation:
    url: str
    title: str
    name: str
    postal_code: str
    insee_code: str
    contains_scores: bool
    scores: Scores
    normalized_scores: Scores
    nearby_cities: List[NearbyCity]
    
    def to_json(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "name": self.name,
            "postal_code": self.postal_code,
            "insee_code": self.insee_code,
            "contains_scores": self.contains_scores,
            "scores": self.scores.to_json(),
            "normalized_scores": self.normalized_scores.to_json(),
            "nearby_cities": [n.to_json() for n in self.nearby_cities]
        }
        
    # def to_record(self) -> dict:
    #     return {
            
    #     }
    
def to_website_url(city_title: str) -> str:
    return f"{WEBSITE_ROOT}/{city_title}/avis.html"

def get_insee_code(city_title: str) -> int:
    m = re.search(r"(\d{5}|\d[A-Z]\d{3})", city_title)
    if m is None:
        raise ValueError(f"No INSEE code found in title {city_title}")
    return m.group(1)

def get_file_content(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()

# ==== Scrapping functions ====

def load_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")

def check_page_contains_scores(soup: BeautifulSoup) -> bool:
    h3 = soup.select_one(".bloc_notemoyenne > h3")
    if h3 is None:
        raise ValueError("No 'bloc_notemoyenne > h3', this should never happen normally")
    return h3.text != "Pas encore d'avis..."

def find_city(soup: BeautifulSoup) -> str:
    # We have something like "Avis Gergny ", we have to clean it
    return (soup.select_one("h1")
            .find(string=True, recursive=False)
            .removeprefix("Avis")
            .strip()
    )

def find_postal_code(soup: BeautifulSoup) -> str:
    return soup.select_one("h1 > small").text

def find_scores(soup: BeautifulSoup) -> Tuple[bool, Scores, Scores]:
    """Returns a tuple with:
        - a flag indicating if the scores were found
        - the scores object
        - the normalized scores object
    """
    contains_scores = check_page_contains_scores(soup)
    if not contains_scores:
        return False, Scores(), Scores()
    
    score_spans = soup.select("table.bloc_chiffre td:nth-child(2) > span:nth-child(1)")
    score_values = [float(s.text) for s in score_spans]
    scores = Scores(*score_values)
    
    return True, scores, scores.normalize()

def find_nearby_cities(soup: BeautifulSoup) -> List[NearbyCity]:
    # Find the table that contains the elements
    rows = soup.select(".tab_compare tbody tr")
    # For each row, we have 7 elements, containing all the information wanted
    def find_infos_for_row(row: Tag) -> NearbyCity:
        tds = row.select("td")
        # The first td contains the city's url
        url = tds[0].find("a", href=True)['href']
        tds = [td.text for td in tds]
        
        # From the city name, we can see if we have any score
        name = tds[0]
        m = re.match(r"(.*) \(.*\)", name)
        contains_scores = m is not None
        if contains_scores:
            name = m.group(1)
        
        return NearbyCity(url, name, contains_scores)
    
    return [find_infos_for_row(row) for row in rows]

# ==== MAIN ====
def save_info(city_title: str, url: str, response, output_folder_path):
    soup = load_soup(response.text)
    url = to_website_url(city_title)
    insee_code = get_insee_code(city_title)
    city = find_city(soup)
    postal_code = find_postal_code(soup)
    
    contains_scores, scores, normalized_scores = find_scores(soup)

    nearby_cities = find_nearby_cities(soup)
    
    city_info = CityInformation(
        url,
        city_title,
        city,
        postal_code,
        insee_code,
        contains_scores,
        scores,
        normalized_scores,
        nearby_cities
    )
    
    output_file_path = output_folder_path / f"{city_title}.html"
    with open(output_file_path, "w", encoding="utf-8") as file:
        json.dump(city_info.to_json(), file)

def load_file_soup(path: Path) -> BeautifulSoup:
    with open(path, "r", encoding="utf-8") as file:
        data = file.read()
        return BeautifulSoup(data, "html.parser")
    
def write_infos_file(info: CityInformation, folder_path: Path):
    output_path = folder_path / f"{info.title}.json"
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(info.to_json(), file)
        
def main():
    args = fetch_arguments()
    
    file_paths = list(args.input_folder_path.glob("*.html"))
    city_info_list = []
    for path in (pbar := tqdm(file_paths)):
        city_title = path.stem
        url = to_website_url(city_title)
        insee_code = get_insee_code(city_title)
        
        pbar.set_description(f"Work on url \"{url}\"")
        
        soup = load_file_soup(path)
        
        city = find_city(soup)
        postal_code = find_postal_code(soup)
        contains_scores, scores, normalized_scores = find_scores(soup)
        nearby_cities = find_nearby_cities(soup)
        
        city_info = CityInformation(
            url,
            city_title,
            city,
            postal_code,
            insee_code,
            contains_scores,
            scores,
            normalized_scores,
            nearby_cities
        )
        
        write_infos_file(city_info, args.output_folder_path)
        
        city_info_list.append(city_info)
        
    # Write all city_infos and put them in a beautiful csv
    df = pd.json_normalize([c.to_json() for c in city_info_list])
    df.to_csv(args.output_folder_path / "!scores.csv")
    
        
if __name__ == "__main__":
    main()