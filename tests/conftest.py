"""
全局测试配置和 fixtures
"""
import asyncio
import os
from typing import AsyncGenerator, Optional
import pytest
import pytest_asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.clients.neo4j_client import neo4j_client


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供整个测试会话使用"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_app():
    """FastAPI应用实例"""
    return app


@pytest.fixture(scope="session") 
def sync_client(test_app):
    """同步测试客户端（用于简单测试）"""
    with TestClient(test_app) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """异步测试客户端"""
    from httpx import ASGITransport
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app), 
        base_url=f"http://testserver{settings.api_prefix}"
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="session")
async def neo4j_session():
    """可选的 Neo4j 连接，会话级共享。

    启用方式：设置环境变量 ENABLE_NEO4J_TEST=1。
    仅在测试显式依赖该 fixture 时才会尝试连接。
    若会话中已由其他途径建立连接（例如使用了 TestClient 触发 lifespan），则复用现有连接。
    """
    if os.getenv("ENABLE_NEO4J_TEST") != "1":
        pytest.skip("ENABLE_NEO4J_TEST not set - skipping neo4j-dependent tests")

    created_here = False
    try:
        if neo4j_client.driver is None:
            await neo4j_client.connect()
            created_here = True
        yield neo4j_client
    finally:
        if created_here:
            try:
                await neo4j_client.disconnect()
            except Exception:
                pass


@pytest.fixture(scope="session")
def s2_api_key() -> Optional[str]:
    """S2 API Key - 用于在线测试"""
    key = os.getenv("S2_API_KEY")
    if not key:
        pytest.skip("S2_API_KEY not set - skipping live tests")
    return key


@pytest.fixture(scope="session")
def paper_id_fixture() -> str:
    """稳定的测试论文ID"""
    # 这是一个真实的S2论文ID，用于测试
    return "649def34f8be52c8b66281af98ae884c09aef38b"


@pytest.fixture(scope="session")  
def doi_fixture() -> str:
    """稳定的测试DOI"""
    return "10.1038/nature14539"


@pytest.fixture(scope="session")
def arxiv_fixture() -> str:
    """稳定的测试ArXiv ID"""
    return "1705.10311"


@pytest.fixture(scope="session")
def search_query_fixture() -> str:
    """稳定的测试搜索查询"""
    return "attention is all you need"


@pytest.fixture(scope="session")
def batch_paper_ids_fixture() -> list[str]:
    """批量测试用的论文ID列表"""
    return [
        "649def34f8be52c8b66281af98ae884c09aef38b",
        "204e3073870fae3d05bcbc2f6a8e263d9b72e776", 
        "0796ca0d52a6ce9b8a9a2b2e5b7e3f8e7b1a4c3d"
    ]


@pytest.fixture
def test_settings():
    """测试环境设置覆盖"""
    return {
        "cache_paper_ttl": 60,  # 短TTL便于测试
        "cache_search_ttl": 30,
        "cache_task_ttl": 10,
        "s2_timeout": 30,
        "max_concurrent_requests": 5
    }


@pytest.fixture
def mock_process_time():
    """模拟处理时间（用于性能测试）"""
    return {
        "cold": 1.5,  # 冷启动时间
        "warm": 0.2,  # 缓存命中时间
        "threshold": 0.3  # 性能阈值
    }


# 条件跳过装饰器
def requires_s2_key(func):
    """需要S2 API Key的测试装饰器"""
    return pytest.mark.skipif(
        not os.getenv("S2_API_KEY"),
        reason="S2_API_KEY not set"
    )(func)


def requires_neo4j(func):
    """需要 Neo4j 连接的测试装饰器（通过 ENABLE_NEO4J_TEST 控制）。"""
    return pytest.mark.skipif(
        os.getenv("ENABLE_NEO4J_TEST") != "1",
        reason="ENABLE_NEO4J_TEST not set"
    )(func)


def slow_test(func):
    """标记慢速测试"""
    return pytest.mark.slow(func)


def flaky_test(func):
    """标记可能不稳定的测试"""
    return pytest.mark.flaky(func)


# 测试数据
@pytest.fixture(scope="session")
def golden_paper_data():
    """黄金样本数据"""
    return {
        "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
        "title": "Attention Is All You Need",
        "year": 2017,
        "authors": [
            {"authorId": "1699545", "name": "Ashish Vaswani"},
            {"authorId": "1692317", "name": "Noam M. Shazeer"}
        ],
        "venue": "NIPS",
        "citationCount": 50000,  # 大概数字
        "referenceCount": 62
    }


@pytest.fixture(scope="session")
def expected_response_fields():
    """期望的响应字段集合"""
    return {
        "basic": {"paperId", "title"},
        "detailed": {
            "paperId", "title", "abstract", "year", "authors",
            "citationCount", "referenceCount", "venue", "url"
        },
        "relations": {"total", "offset", "data"}
    }


@pytest.fixture
async def clean_cache(async_client, paper_id_fixture):
    """清理缓存的辅助fixture"""
    async def _clean():
        # 清理指定论文的缓存
        await async_client.delete(f"/paper/{paper_id_fixture}/cache")
    
    yield _clean
    # 测试后清理
    await _clean()
