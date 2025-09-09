#!/usr/bin/env python3
"""
Simple Neo4j smoke test:
- Prints connection settings
- Connects and health-checks
- MERGEs a dummy paper with authors/externalIds
- Reads it back and prints a short summary
- Prints basic database stats
"""

import asyncio
import json
import os
import sys

# Ensure project root is on sys.path when running directly
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import settings
from app.clients.neo4j_client import neo4j_client


async def main() -> None:
    print(f"NEO4J_URI={settings.neo4j_uri}")
    print(f"NEO4J_USER={settings.neo4j_user}")
    print(f"NEO4J_DATABASE={settings.neo4j_database}")

    await neo4j_client.connect()
    try:
        ok = await neo4j_client.health_check()
        print(f"HEALTH={ok}")

        dummy = {
            "paperId": "test-paper-neo4j-001",
            "title": "Neo4j Test Paper",
            "year": 2025,
            "citationCount": 0,
            "externalIds": {"DOI": "10.1234/test.doi"},
            "authors": [{"authorId": "A-TEST-1", "name": "Test Author"}],
        }

        merged = await neo4j_client.merge_paper(dummy)
        print(f"MERGE={merged}")

        got = await neo4j_client.get_paper(dummy["paperId"])
        print(f"GET={'found' if got else 'missing'}")
        if got:
            summary = {
                "paperId": got.get("paperId"),
                "title": got.get("title"),
                "hasAuthors": bool(got.get("authors")),
                "hasExternalIds": bool(got.get("externalIds")),
                "lastUpdated": str(got.get("lastUpdated")),
            }
            print("DOC=" + json.dumps(summary, ensure_ascii=False))

        stats = await neo4j_client.get_stats()
        print("STATS=" + json.dumps(stats, ensure_ascii=False))
    finally:
        await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())


