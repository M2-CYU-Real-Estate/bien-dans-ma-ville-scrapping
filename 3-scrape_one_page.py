"""Test for scrapping one page, to be used in script 4 i guess...
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Tuple

from bs4 import BeautifulSoup, Tag

WEBSITE_ROOT = "https://www.bien-dans-ma-ville.fr"

WEBSITES_PATH = Path(r"D:\Work\Master\M2\PDS\scrapping\bien-dans-ma-ville\out\websites")

# PAGE_PATH = WEBSITES_PATH / "germignac-17175.html"
PAGE_PATH = WEBSITES_PATH / "gergny-02342.html"

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
        
@dataclass
class NearbyCity:
    url: str
    name: str
    contains_scores: bool
    
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
    
def to_website_url(city_title: str) -> str:
    return f"{WEBSITE_ROOT}/{city_title}/avis.html"

def get_insee_code(page_path: Path) -> int:
    filename = page_path.stem
    return re.search(r"(\d{5})", filename).group(1)

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

def main():
    soup = load_soup(get_file_content(PAGE_PATH))
    
    city_title = PAGE_PATH.stem
    url = to_website_url(city_title)
    insee_code = get_insee_code(PAGE_PATH)
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
    
    print(city_info)
        

if __name__ == "__main__":
    main()