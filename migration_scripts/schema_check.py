"""
Schema 就绪检查脚本：验证关键索引与约束已存在

使用方式：
  make schema-check

退出码：
- 0 表示全部就绪
- 非 0 表示缺失项，需要先执行 make schema-migrate
"""

import asyncio
import os
import sys
from typing import List

from neo4j import AsyncGraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", os.getenv("NEO4J_dbms_default__database", "neo4j"))


REQUIRED_INDEXES: List[str] = [
    "paper_id",
    "paper_title",
    "paper_year",
    "paper_ingest_status",
    "paper_doi",
    "paper_arxiv",
    "paper_dblp",
    "paper_mag",
    "paper_pmid",
    "paper_pmcid",
    "paper_acl",
    "paper_url",
    "paper_corpus_id",
    "datachunk_paper_id",
    "paperFulltext",
    "author_id",
]

REQUIRED_CONSTRAINTS: List[str] = [
    "datachunk_unique",
]


async def list_indexes(session) -> List[str]:
    result = await session.run("SHOW INDEXES")
    names = []
    async for record in result:
        # Neo4j 5: name 字段存放索引名称
        names.append(record.get("name"))
    return names


async def list_constraints(session) -> List[str]:
    result = await session.run("SHOW CONSTRAINTS")
    names = []
    async for record in result:
        names.append(record.get("name"))
    return names


async def check_schema() -> int:
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            exist_indexes = set(await list_indexes(session))
            exist_constraints = set(await list_constraints(session))

            missing_indexes = [i for i in REQUIRED_INDEXES if i not in exist_indexes]
            missing_constraints = [c for c in REQUIRED_CONSTRAINTS if c not in exist_constraints]

            if not missing_indexes and not missing_constraints:
                sys.stdout.write("Schema OK: all required indexes and constraints exist.\n")
                return 0

            if missing_indexes:
                sys.stderr.write("Missing indexes:\n")
                for name in missing_indexes:
                    sys.stderr.write(f"  - {name}\n")
            if missing_constraints:
                sys.stderr.write("Missing constraints:\n")
                for name in missing_constraints:
                    sys.stderr.write(f"  - {name}\n")
            return 2
    finally:
        await driver.close()


def main() -> int:
    try:
        return asyncio.run(check_schema())
    except Exception as exc:
        sys.stderr.write(f"Schema check failed: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


