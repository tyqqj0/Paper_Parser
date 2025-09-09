#!/usr/bin/env python3
"""
Neo4j数据库内容查看器
支持快速查看和调试数据库中的论文、作者、引用关系等信息

使用方法:
  python3 scripts/neo4j_viewer.py                    # 显示基本统计
  python3 scripts/neo4j_viewer.py --papers           # 显示所有论文
  python3 scripts/neo4j_viewer.py --authors          # 显示所有作者
  python3 scripts/neo4j_viewer.py --search "关键词"   # 搜索论文标题
  python3 scripts/neo4j_viewer.py --paper-id "xxx"   # 查看特定论文详情
  python3 scripts/neo4j_viewer.py --author-id "xxx"  # 查看特定作者详情
  python3 scripts/neo4j_viewer.py --limit 10         # 限制结果数量
  python3 scripts/neo4j_viewer.py --clear            # 清空数据库（危险操作）
"""

import asyncio
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

# 确保项目根目录在sys.path中
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.core.config import settings
from app.clients.neo4j_client import neo4j_client


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*20} {title} {'='*20}")
    else:
        print("="*60)


def print_json(data: Any, indent: int = 2):
    """美化打印JSON数据"""
    print(json.dumps(data, ensure_ascii=False, indent=indent, default=str))


async def show_stats():
    """显示数据库统计信息"""
    print_separator("数据库统计")
    stats = await neo4j_client.get_stats()
    print_json(stats)


async def run_custom_query(query: str, params: Dict = None) -> List[Dict]:
    """执行自定义查询"""
    if not neo4j_client.driver:
        return []
    
    async with neo4j_client.driver.session(database=settings.neo4j_database) as session:
        result = await session.run(query, params or {})
        records = []
        async for record in result:
            records.append(record.data())
        return records


async def show_papers(limit: int = 20, search: Optional[str] = None):
    """显示论文列表"""
    print_separator(f"论文列表 (限制{limit}条)")
    
    if search:
        query = """
        MATCH (p:Paper)
        WHERE toLower(p.title) CONTAINS toLower($search)
        RETURN p
        ORDER BY p.lastUpdated DESC
        LIMIT $limit
        """
        params = {"search": search, "limit": limit}
        print(f"搜索关键词: {search}")
    else:
        query = """
        MATCH (p:Paper)
        RETURN p
        ORDER BY p.lastUpdated DESC
        LIMIT $limit
        """
        params = {"limit": limit}
    
    records = await run_custom_query(query, params)
    
    if not records:
        print("没有找到论文")
        return
    
    for i, record in enumerate(records, 1):
        paper = record["p"]
        print(f"\n{i}. {paper.get('title', 'N/A')}")
        print(f"   ID: {paper.get('paperId', 'N/A')}")
        print(f"   年份: {paper.get('year', 'N/A')}")
        print(f"   引用数: {paper.get('citationCount', 0)}")
        print(f"   更新时间: {paper.get('lastUpdated', 'N/A')}")


async def show_authors(limit: int = 20):
    """显示作者列表"""
    print_separator(f"作者列表 (限制{limit}条)")
    
    query = """
    MATCH (a:Author)
    OPTIONAL MATCH (p:Paper)-[:AUTHORED_BY]->(a)
    RETURN a, count(p) as paperCount
    ORDER BY paperCount DESC, a.name
    LIMIT $limit
    """
    
    records = await run_custom_query(query, {"limit": limit})
    
    if not records:
        print("没有找到作者")
        return
    
    for i, record in enumerate(records, 1):
        author = record["a"]
        paper_count = record["paperCount"]
        print(f"\n{i}. {author.get('name', 'N/A')}")
        print(f"   ID: {author.get('authorId', 'N/A')}")
        print(f"   论文数量: {paper_count}")


async def show_paper_details(paper_id: str):
    """显示特定论文的详细信息"""
    print_separator(f"论文详情: {paper_id}")
    
    paper = await neo4j_client.get_paper(paper_id)
    if not paper:
        print("论文未找到")
        return
    
    print("基本信息:")
    print_json({
        "paperId": paper.get("paperId"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "citationCount": paper.get("citationCount"),
        "lastUpdated": paper.get("lastUpdated"),
    })
    
    if paper.get("authors"):
        print("\n作者:")
        for author in paper["authors"]:
            print(f"  - {author.get('name', 'N/A')} (ID: {author.get('authorId', 'N/A')})")
    
    if paper.get("externalIds"):
        print("\n外部ID:")
        print_json(paper["externalIds"])
    
    # 查找引用关系
    query = """
    MATCH (p:Paper {paperId: $paperId})
    OPTIONAL MATCH (p)-[:CITES]->(cited:Paper)
    OPTIONAL MATCH (citing:Paper)-[:CITES]->(p)
    RETURN 
        collect(DISTINCT cited.paperId) as citedPapers,
        collect(DISTINCT citing.paperId) as citingPapers
    """
    
    records = await run_custom_query(query, {"paperId": paper_id})
    if records:
        record = records[0]
        cited = [pid for pid in record["citedPapers"] if pid]
        citing = [pid for pid in record["citingPapers"] if pid]
        
        if cited:
            print(f"\n引用的论文 ({len(cited)}篇):")
            for pid in cited[:5]:  # 只显示前5个
                print(f"  - {pid}")
            if len(cited) > 5:
                print(f"  ... 还有{len(cited)-5}篇")
        
        if citing:
            print(f"\n被引用的论文 ({len(citing)}篇):")
            for pid in citing[:5]:  # 只显示前5个
                print(f"  - {pid}")
            if len(citing) > 5:
                print(f"  ... 还有{len(citing)-5}篇")


async def show_author_details(author_id: str):
    """显示特定作者的详细信息"""
    print_separator(f"作者详情: {author_id}")
    
    query = """
    MATCH (a:Author {authorId: $authorId})
    OPTIONAL MATCH (p:Paper)-[:AUTHORED_BY]->(a)
    RETURN a, collect(p) as papers
    """
    
    records = await run_custom_query(query, {"authorId": author_id})
    if not records:
        print("作者未找到")
        return
    
    record = records[0]
    author = record["a"]
    papers = record["papers"]
    
    print("基本信息:")
    print_json({
        "authorId": author.get("authorId"),
        "name": author.get("name"),
        "paperCount": len(papers),
    })
    
    if papers:
        print(f"\n发表的论文 ({len(papers)}篇):")
        for paper in papers[:10]:  # 只显示前10篇
            print(f"  - {paper.get('title', 'N/A')} ({paper.get('year', 'N/A')})")
        if len(papers) > 10:
            print(f"  ... 还有{len(papers)-10}篇")


async def clear_database():
    """清空数据库（危险操作）"""
    print_separator("清空数据库")
    
    # 再次确认
    confirm = input("⚠️  这将删除所有数据！请输入 'YES' 确认: ")
    if confirm != "YES":
        print("操作已取消")
        return
    
    query = "MATCH (n) DETACH DELETE n"
    await run_custom_query(query)
    print("✅ 数据库已清空")


async def main():
    parser = argparse.ArgumentParser(
        description="Neo4j数据库内容查看器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("--papers", action="store_true", help="显示论文列表")
    parser.add_argument("--authors", action="store_true", help="显示作者列表")
    parser.add_argument("--search", type=str, help="搜索论文标题")
    parser.add_argument("--paper-id", type=str, help="查看特定论文详情")
    parser.add_argument("--author-id", type=str, help="查看特定作者详情")
    parser.add_argument("--limit", type=int, default=20, help="限制结果数量")
    parser.add_argument("--clear", action="store_true", help="清空数据库（危险操作）")
    
    args = parser.parse_args()
    
    print(f"连接到Neo4j: {settings.neo4j_uri}")
    print(f"数据库: {settings.neo4j_database}")
    
    await neo4j_client.connect()
    try:
        # 检查连接
        health = await neo4j_client.health_check()
        if not health:
            print("❌ Neo4j连接失败")
            return
        
        print("✅ Neo4j连接成功")
        
        # 根据参数执行相应操作
        if args.clear:
            await clear_database()
        elif args.paper_id:
            await show_paper_details(args.paper_id)
        elif args.author_id:
            await show_author_details(args.author_id)
        elif args.papers or args.search:
            await show_papers(args.limit, args.search)
        elif args.authors:
            await show_authors(args.limit)
        else:
            # 默认显示统计信息
            await show_stats()
    
    finally:
        await neo4j_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
