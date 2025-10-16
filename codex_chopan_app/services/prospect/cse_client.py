"""Deterministic client for custom search."""
from __future__ import annotations

from typing import List


class CustomSearchClient:
    SAMPLE_DATA = [
        {"organization": "Chopan Foundation", "website": "https://chopan.example.org"},
        {"organization": "Global Arts Alliance", "website": "https://arts.example.org"},
        {"organization": "AI Storytelling Lab", "website": "https://story.ai"},
    ]

    def search(self, query: str, limit: int) -> List[dict[str, str]]:
        keyword = query.lower().split()[0]
        results = [item for item in self.SAMPLE_DATA if keyword in item["organization"].lower()]
        if len(results) < limit:
            for item in self.SAMPLE_DATA:
                if item not in results:
                    results.append(item)
                if len(results) >= limit:
                    break
        return results[:limit]
