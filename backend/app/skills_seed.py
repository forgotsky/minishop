from typing import List, Dict, Any
from .skills_data import get_skills
from .repository import upsert_category


def seed_skills(db) -> int:
    data: List[Dict[str, Any]] = get_skills()
    count = 0
    for category in data:
        upsert_category(db, category, source="seed")
        count += 1
    return count
