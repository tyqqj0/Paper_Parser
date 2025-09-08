"""
基础测试用例
"""
import pytest
import asyncio
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """测试根路径"""
    response = await client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert "Paper Parser API" in data["data"]["service"]


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """测试健康检查"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_detailed_endpoint(client):
    """测试详细健康检查"""
    response = await client.get("/api/v1/health/detailed")
    
    # 由于测试环境可能没有真实的数据库连接，状态码可能不是200
    # 但应该有响应结构
    data = response.json()
    assert "success" in data
    assert "data" in data
    
    if response.status_code == 200:
        assert data["data"]["status"] in ["healthy", "degraded"]
        assert "services" in data["data"]


@pytest.mark.asyncio
async def test_paper_endpoint_validation():
    """测试论文接口参数验证"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试无效的paper_id
        response = await client.get("/api/v1/paper/invalid-id")
        # 由于没有真实的S2连接，预期会有错误
        assert response.status_code in [404, 500]


@pytest.mark.asyncio  
async def test_search_endpoint_validation():
    """测试搜索接口参数验证"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试缺少query参数
        response = await client.get("/api/v1/paper/search")
        assert response.status_code == 422  # 参数验证错误
        
        # 测试无效的limit参数
        response = await client.get("/api/v1/paper/search?query=test&limit=1000")
        assert response.status_code == 422  # 超过最大限制


@pytest.mark.asyncio
async def test_batch_endpoint_validation():
    """测试批量接口参数验证"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试空的ids列表
        response = await client.post(
            "/api/v1/paper/batch",
            json={"ids": []}
        )
        # 应该接受空列表但返回空结果
        assert response.status_code in [200, 400]
        
        # 测试过多的ids
        large_ids = ["id"] * 501
        response = await client.post(
            "/api/v1/paper/batch", 
            json={"ids": large_ids}
        )
        assert response.status_code == 400  # 超过限制


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
