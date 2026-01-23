"""
Módulo de web scraping para descarga automatizada de portales EPS
"""
from .familiar_scraper import FamiliarScraper
from .fomag_scraper import FomagScraper

__all__ = ["FamiliarScraper", "FomagScraper"]
