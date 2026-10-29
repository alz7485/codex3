"""Synthetic trophy for engine/record contracts, independent of shipped pacing."""
from copy import deepcopy
from pathlib import Path
from companion.growth_content import read_json

def add_test_trophy(catalog):
    old=read_json(Path(__file__).parents[1]/'companion/assets/growth_migrations/v0350.json')
    item=deepcopy(old['base']['trophies'][0]);item.update(key='base:first_hour',root=Path(__file__).parents[1]/'companion/assets/growth/base')
    catalog.items['trophies'][item['key']]=item
