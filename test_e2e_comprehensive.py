#!/usr/bin/env python3
"""
端到端综合测试文件 - 测试Paper Parser API的各种查询场景
包括：全字段查询、部分字段查询、别名查询、缓存验证、S2 API对齐等

使用方法:
python test_e2e_comprehensive.py

或指定特定测试:
python test_e2e_comprehensive.py --test full_fields
"""

import asyncio
import aiohttp
import json
import time
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from colorama import init, Fore, Style

# 初始化colorama用于彩色输出
init(autoreset=True)

@dataclass
class TestCase:
    name: str
    description: str
    paper_id: str
    fields: Optional[List[str]] = None
    expected_keys: Optional[List[str]] = None
    should_have_cache: bool = False

class E2ETestSuite:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api/v1"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results = []
        
        # 测试用的论文ID - 使用一些知名论文确保S2有数据
        self.test_papers = {
            "attention": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",  # Attention Is All You Need
            "bert": "df2b0e26d0599ce3e70df8a9da02e51594e0e992",      # BERT
            "gpt": "cd18800a0fe0b668a1cc19f2ec95b5003d0a5035",       # GPT
            "resnet": "2c03df8b48bf3fa39054345bafabfeff15bfd11d",    # ResNet
            "transformer": "0204e3073870fae3d05bcbc2f6a8e263d9b72e776" # Transformer (backup)
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def print_section(self, title: str):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}{title}")
        print(f"{Fore.CYAN}{'='*60}")

    def print_test_start(self, test_name: str, description: str):
        print(f"\n{Fore.YELLOW}🧪 测试: {test_name}")
        print(f"{Fore.WHITE}📝 描述: {description}")

    def print_success(self, message: str):
        print(f"{Fore.GREEN}✅ {message}")

    def print_warning(self, message: str):
        print(f"{Fore.YELLOW}⚠️  {message}")

    def print_error(self, message: str):
        print(f"{Fore.RED}❌ {message}")

    async def make_request(self, endpoint: str, params: Dict[str, Any] = None) -> tuple[int, Dict]:
        """发送HTTP请求并返回状态码和响应数据"""
        url = f"{self.base_url}{endpoint}"
        try:
            start_time = time.time()
            async with self.session.get(url, params=params) as response:
                response_time = time.time() - start_time
                data = await response.json()
                print(f"📊 请求耗时: {response_time:.3f}s | 状态码: {response.status}")
                return response.status, data
        except Exception as e:
            self.print_error(f"请求失败: {e}")
            return 500, {"error": str(e)}

    def validate_paper_structure(self, paper_data: Dict, expected_keys: List[str] = None) -> bool:
        """验证论文数据结构"""
        if not isinstance(paper_data, dict):
            self.print_error("响应不是字典格式")
            return False

        # 基本必需字段
        required_base_keys = ["paperId", "title"]
        for key in required_base_keys:
            if key not in paper_data:
                self.print_error(f"缺少必需字段: {key}")
                return False

        # 检查期望的字段
        if expected_keys:
            missing_keys = []
            for key in expected_keys:
                if key not in paper_data:
                    missing_keys.append(key)
            
            if missing_keys:
                self.print_warning(f"缺少期望字段: {missing_keys}")
                return False

        self.print_success(f"数据结构验证通过，包含 {len(paper_data)} 个字段")
        return True

    def compare_with_s2_format(self, our_data: Dict, test_name: str):
        """与S2 API格式对比"""
        print(f"\n{Fore.BLUE}🔍 S2格式对比分析:")
        
        # 检查关键字段的数据类型和结构
        type_checks = {
            "paperId": str,
            "title": str,
            "year": (int, type(None)),
            "citationCount": (int, type(None)),
            "referenceCount": (int, type(None)),
            "authors": list,
            "venue": (str, type(None)),
            "abstract": (str, type(None))
        }

        for field, expected_type in type_checks.items():
            if field in our_data:
                actual_type = type(our_data[field])
                if isinstance(expected_type, tuple):
                    if actual_type not in expected_type:
                        self.print_warning(f"{field}: 类型不匹配 (期望: {expected_type}, 实际: {actual_type})")
                    else:
                        self.print_success(f"{field}: 类型正确 ({actual_type.__name__})")
                else:
                    if actual_type != expected_type:
                        self.print_warning(f"{field}: 类型不匹配 (期望: {expected_type.__name__}, 实际: {actual_type.__name__})")
                    else:
                        self.print_success(f"{field}: 类型正确 ({actual_type.__name__})")

        # 检查authors结构
        if "authors" in our_data and our_data["authors"]:
            author = our_data["authors"][0]
            if isinstance(author, dict):
                author_fields = ["authorId", "name"]
                for field in author_fields:
                    if field in author:
                        self.print_success(f"authors[0].{field}: 存在")
                    else:
                        self.print_warning(f"authors[0].{field}: 缺失")

    async def test_full_fields_query(self) -> bool:
        """测试1: 全字段查询"""
        self.print_test_start("全字段查询", "查询论文的所有可用字段")
        
        paper_id = self.test_papers["attention"]
        status, data = await self.make_request(f"/paper/{paper_id}")
        
        if status != 200:
            self.print_error(f"请求失败，状态码: {status}")
            return False

        # 验证数据结构
        if not self.validate_paper_structure(data):
            return False

        # 显示返回的字段
        print(f"\n{Fore.BLUE}📋 返回的字段 ({len(data)} 个):")
        for key, value in data.items():
            value_preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"  • {key}: {type(value).__name__} = {value_preview}")

        # S2格式对比
        self.compare_with_s2_format(data, "全字段查询")
        
        return True

    async def test_partial_fields_query(self) -> bool:
        """测试2: 部分字段查询"""
        self.print_test_start("部分字段查询", "只查询指定的字段子集")
        
        paper_id = self.test_papers["bert"]
        requested_fields = ["paperId", "title", "year", "authors", "citationCount"]
        
        params = {"fields": ",".join(requested_fields)}
        status, data = await self.make_request(f"/paper/{paper_id}", params)
        
        if status != 200:
            self.print_error(f"请求失败，状态码: {status}")
            return False

        # 验证只返回了请求的字段
        returned_fields = set(data.keys())
        requested_fields_set = set(requested_fields)
        
        print(f"\n{Fore.BLUE}📋 字段对比:")
        print(f"  请求字段: {requested_fields}")
        print(f"  返回字段: {list(returned_fields)}")
        
        # 检查是否有多余字段
        extra_fields = returned_fields - requested_fields_set
        if extra_fields:
            self.print_warning(f"返回了额外字段: {extra_fields}")
        
        # 检查是否有缺失字段
        missing_fields = requested_fields_set - returned_fields
        if missing_fields:
            self.print_error(f"缺失请求字段: {missing_fields}")
            return False
        
        self.print_success("字段过滤正确")
        self.compare_with_s2_format(data, "部分字段查询")
        
        return True

    async def test_alias_queries(self) -> bool:
        """测试3: 别名查询"""
        self.print_test_start("别名查询", "使用DOI、ArXiv ID等别名查询论文")
        
        # 测试用例：使用不同的别名格式
        alias_tests = [
            {
                "name": "ArXiv ID查询", 
                "alias": "1706.03762",  # Attention Is All You Need的ArXiv ID
                "expected_title_contains": "Attention"
            },
            {
                "name": "DOI查询",
                "alias": "10.18653/v1/N16-1030",  # 一个已知DOI
                "expected_title_contains": ""  # 不强制要求特定标题
            }
        ]
        
        success_count = 0
        for test in alias_tests:
            print(f"\n{Fore.YELLOW}🔍 子测试: {test['name']}")
            print(f"  查询别名: {test['alias']}")
            
            status, data = await self.make_request(f"/paper/{test['alias']}")
            
            if status == 200:
                self.print_success(f"别名查询成功: {test['alias']}")
                if "title" in data:
                    print(f"  📄 标题: {data['title']}")
                    if test['expected_title_contains'] and test['expected_title_contains'].lower() in data['title'].lower():
                        self.print_success("标题匹配预期")
                    success_count += 1
                else:
                    self.print_warning("响应中缺少标题字段")
            elif status == 404:
                self.print_warning(f"别名未找到: {test['alias']} (这可能是正常的)")
            else:
                self.print_error(f"别名查询失败: {status}")
        
        return success_count > 0

    async def test_cache_behavior(self) -> bool:
        """测试4: 缓存行为验证"""
        self.print_test_start("缓存行为验证", "验证缓存命中和性能")
        
        paper_id = self.test_papers["gpt"]
        
        # 第一次请求（可能会触发缓存）
        print(f"{Fore.BLUE}🔄 第一次请求 (可能从S2获取):")
        start_time = time.time()
        status1, data1 = await self.make_request(f"/paper/{paper_id}")
        first_request_time = time.time() - start_time
        
        if status1 != 200:
            self.print_error("第一次请求失败")
            return False
        
        # 等待一小段时间确保缓存生效
        await asyncio.sleep(0.1)
        
        # 第二次请求（应该命中缓存）
        print(f"\n{Fore.BLUE}🔄 第二次请求 (应该命中缓存):")
        start_time = time.time()
        status2, data2 = await self.make_request(f"/paper/{paper_id}")
        second_request_time = time.time() - start_time
        
        if status2 != 200:
            self.print_error("第二次请求失败")
            return False
        
        # 比较响应时间
        print(f"\n{Fore.BLUE}⏱️  性能对比:")
        print(f"  第一次请求: {first_request_time:.3f}s")
        print(f"  第二次请求: {second_request_time:.3f}s")
        
        if second_request_time < first_request_time * 0.8:  # 缓存应该快至少20%
            self.print_success("缓存性能提升明显")
        else:
            self.print_warning("缓存性能提升不明显，可能未命中缓存")
        
        # 比较数据一致性
        if data1 == data2:
            self.print_success("两次请求数据完全一致")
        else:
            self.print_warning("两次请求数据不一致")
            # 显示差异
            keys1, keys2 = set(data1.keys()), set(data2.keys())
            if keys1 != keys2:
                print(f"  字段差异: {keys1.symmetric_difference(keys2)}")
        
        return True

    async def test_error_handling(self) -> bool:
        """测试5: 错误处理"""
        self.print_test_start("错误处理", "测试各种错误情况的处理")
        
        error_tests = [
            {
                "name": "不存在的论文ID",
                "paper_id": "nonexistent123456789",
                "expected_status": 404
            },
            {
                "name": "无效的论文ID格式",
                "paper_id": "invalid-format-!@#",
                "expected_status": [400, 404]  # 可能是400或404
            }
        ]
        
        success_count = 0
        for test in error_tests:
            print(f"\n{Fore.YELLOW}🔍 子测试: {test['name']}")
            status, data = await self.make_request(f"/paper/{test['paper_id']}")
            
            expected_statuses = test['expected_status'] if isinstance(test['expected_status'], list) else [test['expected_status']]
            
            if status in expected_statuses:
                self.print_success(f"错误状态码正确: {status}")
                if "error" in data or "message" in data:
                    self.print_success("包含错误信息")
                success_count += 1
            else:
                self.print_error(f"期望状态码 {expected_statuses}，实际 {status}")
        
        return success_count == len(error_tests)

    async def test_fields_parameter(self) -> bool:
        """测试6: fields参数的各种格式"""
        self.print_test_start("fields参数测试", "测试fields参数的不同格式和组合")
        
        paper_id = self.test_papers["resnet"]
        
        field_tests = [
            {
                "name": "单个字段",
                "fields": "title",
                "expected": ["paperId", "title"]  # paperId总是返回
            },
            {
                "name": "多个字段（逗号分隔）",
                "fields": "title,year,authors",
                "expected": ["paperId", "title", "year", "authors"]
            },
            {
                "name": "包含关系字段",
                "fields": "title,references,citations",
                "expected": ["paperId", "title", "references", "citations"]
            },
            {
                "name": "所有基础字段",
                "fields": "paperId,title,abstract,venue,year,referenceCount,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationDate,journal,authors",
                "expected": None  # 不检查特定字段，只检查请求成功
            }
        ]
        
        success_count = 0
        for test in field_tests:
            print(f"\n{Fore.YELLOW}🔍 子测试: {test['name']}")
            print(f"  请求字段: {test['fields']}")
            
            params = {"fields": test['fields']}
            status, data = await self.make_request(f"/paper/{paper_id}", params)
            
            if status == 200:
                returned_fields = list(data.keys())
                print(f"  返回字段: {returned_fields}")
                
                if test['expected']:
                    expected_set = set(test['expected'])
                    returned_set = set(returned_fields)
                    
                    if expected_set.issubset(returned_set):
                        self.print_success("包含所有期望字段")
                        success_count += 1
                    else:
                        missing = expected_set - returned_set
                        self.print_error(f"缺少字段: {missing}")
                else:
                    self.print_success("请求成功")
                    success_count += 1
            else:
                self.print_error(f"请求失败: {status}")
        
        return success_count == len(field_tests)

    async def run_health_check(self) -> bool:
        """运行健康检查"""
        self.print_section("🏥 系统健康检查")
        
        # 检查API是否运行
        try:
            status, data = await self.make_request("/health")
            if status == 200:
                self.print_success("API服务运行正常")
                return True
            else:
                self.print_error(f"健康检查失败: {status}")
                return False
        except Exception as e:
            self.print_error(f"无法连接到API服务: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        self.print_section("🚀 Paper Parser API 端到端测试套件")
        
        # 健康检查
        if not await self.run_health_check():
            self.print_error("健康检查失败，停止测试")
            return
        
        # 定义测试套件
        tests = [
            ("全字段查询", self.test_full_fields_query),
            ("部分字段查询", self.test_partial_fields_query),
            ("别名查询", self.test_alias_queries),
            ("缓存行为验证", self.test_cache_behavior),
            ("错误处理", self.test_error_handling),
            ("fields参数测试", self.test_fields_parameter),
        ]
        
        # 运行测试
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed += 1
                    self.test_results.append({"name": test_name, "status": "PASSED"})
                else:
                    failed += 1
                    self.test_results.append({"name": test_name, "status": "FAILED"})
            except Exception as e:
                failed += 1
                self.print_error(f"测试 '{test_name}' 抛出异常: {e}")
                self.test_results.append({"name": test_name, "status": "ERROR", "error": str(e)})
        
        # 显示测试总结
        self.print_section("📊 测试结果总结")
        print(f"{Fore.GREEN}✅ 通过: {passed}")
        print(f"{Fore.RED}❌ 失败: {failed}")
        print(f"{Fore.BLUE}📋 总计: {passed + failed}")
        
        print(f"\n{Fore.BLUE}详细结果:")
        for result in self.test_results:
            status_color = Fore.GREEN if result["status"] == "PASSED" else Fore.RED
            print(f"  {status_color}{result['status']}: {result['name']}")
            if "error" in result:
                print(f"    {Fore.RED}错误: {result['error']}")
        
        # 给出建议
        if failed == 0:
            print(f"\n{Fore.GREEN}🎉 所有测试通过！API工作正常。")
        else:
            print(f"\n{Fore.YELLOW}⚠️  有 {failed} 个测试失败，请检查相关功能。")

    async def run_specific_test(self, test_name: str):
        """运行特定测试"""
        test_map = {
            "health": self.run_health_check,
            "full_fields": self.test_full_fields_query,
            "partial_fields": self.test_partial_fields_query,
            "alias": self.test_alias_queries,
            "cache": self.test_cache_behavior,
            "error": self.test_error_handling,
            "fields_param": self.test_fields_parameter,
        }
        
        if test_name not in test_map:
            self.print_error(f"未知测试: {test_name}")
            print(f"可用测试: {', '.join(test_map.keys())}")
            return
        
        self.print_section(f"🧪 运行单个测试: {test_name}")
        
        if not await self.run_health_check():
            self.print_error("健康检查失败，停止测试")
            return
        
        try:
            result = await test_map[test_name]()
            if result:
                self.print_success(f"测试 '{test_name}' 通过")
            else:
                self.print_error(f"测试 '{test_name}' 失败")
        except Exception as e:
            self.print_error(f"测试 '{test_name}' 抛出异常: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Paper Parser API 端到端测试")
    parser.add_argument("--test", help="运行特定测试 (health, full_fields, partial_fields, alias, cache, error, fields_param)")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1", help="API服务URL")
    
    args = parser.parse_args()
    
    async with E2ETestSuite(args.url) as test_suite:
        if args.test:
            await test_suite.run_specific_test(args.test)
        else:
            await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
