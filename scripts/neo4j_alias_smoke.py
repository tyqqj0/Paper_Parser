#!/usr/bin/env python3
"""
Neo4j alias resolution & ingest-plan smoke test

Validates:
- MERGE paper with rich externalIds
- MERGE aliases (with :Alias label)
- get_paper_by_alias() for prefixed and raw inputs
- create_citations_ingest_plan() creation
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List


# Ensure project root is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import settings
from app.clients.neo4j_client import neo4j_client


TEST_PAPER_ID = "test-paper-alias-001"


async def assert_alias_hit(label: str, identifier: str) -> bool:
    doc = await neo4j_client.get_paper_by_alias(identifier)
    ok = bool(doc and doc.get("paperId") == TEST_PAPER_ID)
    print(f"ALIAS[{label}] {identifier} -> {'OK' if ok else 'FAIL'}")
    return ok


async def check_alias_labels(expected: List[Dict[str, str]]) -> bool:
    if neo4j_client.driver is None:
        return False
    query = (
        """
        UNWIND $pairs AS row
        MATCH (e:ExternalId:Alias {type: row.type, value: row.value})
        RETURN count(e) AS c
        """
    )
    async with neo4j_client.driver.session(database=settings.neo4j_database) as session:
        for pair in expected:
            try:
                result = await session.run(query, pairs=[pair])
                rec = await result.single()
                ok = rec and rec.get("c", 0) >= 1
                print(
                    "ALIAS_LABEL",
                    f"type={pair['type']} value={pair['value']} -> {'OK' if ok else 'MISSING'}",
                )
                if not ok:
                    return False
            except Exception as e:
                print("ALIAS_LABEL_ERR", pair, e)
                return False
    return True


async def check_plan_created(total: int, page_size: int) -> bool:
    if neo4j_client.driver is None:
        return False
    query = (
        """
        MATCH (:Paper {paperId: $paper_id})-[:HAS_CITATIONS_PLAN]->(plan:PaperCitationsPlan)
        WHERE plan.chunkType = 'citations_plan' AND plan.total = $total AND plan.pageSize = $page_size
        RETURN count(plan) AS c
        """
    )
    async with neo4j_client.driver.session(database=settings.neo4j_database) as session:
        try:
            result = await session.run(
                query, paper_id=TEST_PAPER_ID, total=total, page_size=page_size
            )
            rec = await result.single()
            ok = rec and rec.get("c", 0) >= 1
            print(f"PLAN_CREATED -> {'OK' if ok else 'MISSING'}")
            return ok
        except Exception as e:
            print("PLAN_CHECK_ERR", e)
            return False


async def main() -> None:
    print(f"NEO4J_URI={settings.neo4j_uri}")
    print(f"NEO4J_USER={settings.neo4j_user}")
    print(f"NEO4J_DATABASE={settings.neo4j_database}")

    await neo4j_client.connect()
    try:
        ok = await neo4j_client.health_check()
        print(f"HEALTH={ok}")
        if not ok:
            return

        # 1) Merge test paper with rich aliases
        test = {
            "paperId": TEST_PAPER_ID,
            "title": "Alias Resolution Test: PMCID/PMID/MAG/ACL",
            "year": 2024,
            "citationCount": 500,
            "referenceCount": 10,
            "externalIds": {
                "DOI": "10.1145/1234567.8901234",
                "ArXiv": "arXiv:2106.15928v2",
                "CorpusId": 215412,
                "URL": "https://example.com/SomePath/?utm_source=foo&y=1",
                "MAG": 123456789,
                "ACL": "P23-1001",
                "PMID": 12345678,
                "PMCID": "PMC9876543",
            },
            "authors": [
                {"authorId": "A-ALIAS-1", "name": "Alias Author"},
            ],
        }

        merged = await neo4j_client.merge_paper(test)
        print(f"MERGE={merged}")

        # 2) Ensure aliases (with :Alias label) are merged
        await neo4j_client.merge_aliases_from_paper(test)

        # Expected normalized URL value
        norm_url = "https://example.com/SomePath?y=1"

        # Verify alias label presence for a few key IDs
        await check_alias_labels(
            [
                {"type": "DOI", "value": "10.1145/1234567.8901234"},
                {"type": "ArXiv", "value": "2106.15928"},
                {"type": "CorpusId", "value": "215412"},
                {"type": "URL", "value": norm_url},
                {"type": "MAG", "value": "123456789"},
                {"type": "ACL", "value": "P23-1001"},
                {"type": "PMID", "value": "12345678"},
                {"type": "PMCID", "value": "9876543"},
            ]
        )

        # 3) Test alias resolutions (prefixed + raw)
        results = []
        results.append(await assert_alias_hit("DOI:prefixed", "DOI:10.1145/1234567.8901234"))
        results.append(await assert_alias_hit("DOI:raw", "10.1145/1234567.8901234"))
        results.append(await assert_alias_hit("ARXIV:prefixed", "ARXIV:2106.15928"))
        results.append(await assert_alias_hit("arXiv:raw-with-version", "arXiv:2106.15928v2"))
        results.append(await assert_alias_hit("CorpusId:prefixed", "CorpusId:215412"))
        results.append(await assert_alias_hit("CorpusId:raw", "215412"))
        results.append(await assert_alias_hit("URL:prefixed", f"URL:{norm_url}"))
        results.append(await assert_alias_hit("MAG:prefixed", "MAG:123456789"))
        results.append(await assert_alias_hit("ACL:prefixed", "ACL:P23-1001"))
        results.append(await assert_alias_hit("PMID:prefixed", "PMID:12345678"))
        results.append(await assert_alias_hit("PMCID:prefixed", "PMCID:PMC9876543"))

        # Title-based strong match
        results.append(await assert_alias_hit("TITLE_NORM", test["title"]))

        # 4) Create ingest plan for large citations
        plan_total = 500
        page_size = 200
        plan_ok = await neo4j_client.create_citations_ingest_plan(
            TEST_PAPER_ID, plan_total, page_size
        )
        print(f"PLAN_MERGE={plan_ok}")
        await check_plan_created(plan_total, page_size)

        # 5) Dump all ExternalId attached to the test paper for inspection
        if neo4j_client.driver is not None:
            q = (
                """
                MATCH (:Paper {paperId: $paper_id})-[:HAS_EXTERNAL_ID]->(e:ExternalId)
                RETURN e.type AS type, e.value AS value, labels(e) AS labels
                ORDER BY type, value
                """
            )
            async with neo4j_client.driver.session(database=settings.neo4j_database) as session:
                res = await session.run(q, paper_id=TEST_PAPER_ID)
                rows = []
                async for r in res:
                    rows.append(r.data())
                print("EXTERNAL_IDS=" + json.dumps(rows, ensure_ascii=False))

        passed = sum(1 for x in results if x)
        print("SUMMARY=" + json.dumps({"total": len(results), "passed": passed}))

    finally:
        await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())


