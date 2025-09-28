"""
离线/一次性模式迁移脚本：创建 Neo4j 索引与约束

使用方式：
  make schema-migrate

说明：
- 仅执行创建（IF NOT EXISTS），可重复运行且幂等
- 串行执行，最大限度减少标签锁竞争
- 结束后等待索引可用
"""

import asyncio
import os
import sys
from typing import List

from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", os.getenv("NEO4J_dbms_default__database", "neo4j"))


SCHEMA_STATEMENTS: List[str] = [
    # Paper 索引
    "CREATE INDEX paper_id IF NOT EXISTS FOR (p:Paper) ON (p.paperId)",
    "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
    "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
    "CREATE INDEX paper_ingest_status IF NOT EXISTS FOR (p:Paper) ON (p.ingestStatus)",


    # DataChunk 索引与唯一约束
    "CREATE INDEX datachunk_paper_id IF NOT EXISTS FOR (d:DataChunk) ON (d.paperId)",
    "CREATE CONSTRAINT datachunk_unique IF NOT EXISTS FOR (d:DataChunk) REQUIRE (d.paperId, d.chunkType) IS UNIQUE",

    # 全文索引
    "CREATE FULLTEXT INDEX paperFulltext IF NOT EXISTS FOR (p:Paper) ON EACH [p.title]",

    # Author 索引
    "CREATE INDEX author_id IF NOT EXISTS FOR (a:Author) ON (a.authorId)",
]


async def await_indexes(driver) -> None:
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run("CALL db.awaitIndexes(300)")


async def run_schema_migration() -> None:
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        async with driver.session(database=NEO4J_DATABASE) as session:
            for stmt in SCHEMA_STATEMENTS:
                try:
                    await session.run(stmt)
                    # 小幅让渡，减少锁保持时间
                    await asyncio.sleep(0.05)
                    sys.stdout.write(f"[OK] {stmt}\n")
                except Neo4jError as e:
                    # IF NOT EXISTS 情况下，仍可能因并发或权限触发错误
                    sys.stderr.write(f"[WARN] {stmt} -> {e.code}: {e.message}\n")
                    # 继续后续语句，保证尽可能多的语句被执行
        await await_indexes(driver)
        sys.stdout.write("All indexes are online.\n")
    finally:
        await driver.close()


def main() -> int:
    try:
        asyncio.run(run_schema_migration())
        return 0
    except Exception as exc:
        sys.stderr.write(f"Migration failed: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


