#!/usr/bin/env python3
"""
SQLite别名映射查看器
用于查看和分析external_id_mapping.db中的别名映射数据
"""

import sqlite3
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from tabulate import tabulate

# 支持的外部ID类型
EXTERNAL_ID_TYPES = {
    "DOI", "ArXiv", "CorpusId", "MAG", "ACL", "PMID", "PMCID", "URL", "TITLE_NORM", "DBLP"
}

class SQLiteAliasViewer:
    """SQLite别名映射查看器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
    
    def _connect(self) -> sqlite3.Connection:
        """连接数据库"""
        return sqlite3.connect(self.db_path)
    
    def show_table_info(self):
        """显示表结构信息"""
        print("\n=== 表结构信息 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 获取表结构
            cursor.execute("PRAGMA table_info(external_id_mappings)")
            columns = cursor.fetchall()
            
            if not columns:
                print("❌ 表 external_id_mappings 不存在")
                return
            
            # 格式化显示列信息
            headers = ["列名", "类型", "非空", "默认值", "主键"]
            table_data = []
            for col in columns:
                table_data.append([
                    col[1],  # name
                    col[2],  # type
                    "是" if col[3] else "否",  # notnull
                    col[4] or "",  # default_value
                    "是" if col[5] else "否"   # pk
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            # 获取索引信息
            cursor.execute("PRAGMA index_list(external_id_mappings)")
            indexes = cursor.fetchall()
            
            if indexes:
                print("\n📋 索引信息:")
                for idx in indexes:
                    print(f"  - {idx[1]} ({'唯一' if idx[2] else '普通'})")
    
    def show_statistics(self):
        """显示统计信息"""
        print("\n=== 统计信息 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 总映射数
            cursor.execute("SELECT COUNT(*) FROM external_id_mappings")
            total_count = cursor.fetchone()[0]
            print(f"📊 总映射数: {total_count:,}")
            
            # 唯一论文数
            cursor.execute("SELECT COUNT(DISTINCT paper_id) FROM external_id_mappings")
            unique_papers = cursor.fetchone()[0]
            print(f"📄 唯一论文数: {unique_papers:,}")
            
            # 平均别名数
            if unique_papers > 0:
                avg_aliases = total_count / unique_papers
                print(f"📈 平均别名数: {avg_aliases:.2f}")
            
            # 按类型统计
            cursor.execute("""
                SELECT external_type, COUNT(*) 
                FROM external_id_mappings 
                GROUP BY external_type 
                ORDER BY COUNT(*) DESC
            """)
            type_stats = cursor.fetchall()
            
            if type_stats:
                print("\n📋 按类型统计:")
                headers = ["类型", "数量", "占比"]
                table_data = []
                for type_name, count in type_stats:
                    percentage = (count / total_count * 100) if total_count > 0 else 0
                    table_data.append([type_name, f"{count:,}", f"{percentage:.1f}%"])
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def show_recent_mappings(self, limit: int = 10):
        """显示最近的映射"""
        print(f"\n=== 最近 {limit} 条映射 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT external_type, external_id, paper_id, 
                       datetime(created_at, 'unixepoch') as created,
                       datetime(updated_at, 'unixepoch') as updated
                FROM external_id_mappings 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            
            if not results:
                print("❌ 没有找到映射记录")
                return
            
            headers = ["类型", "外部ID", "论文ID", "创建时间", "更新时间"]
            table_data = []
            for row in results:
                # 截断长ID以便显示
                external_id = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
                paper_id = row[2][:30] + "..." if len(row[2]) > 30 else row[2]
                
                table_data.append([
                    row[0],  # type
                    external_id,
                    paper_id,
                    row[3] or "未知",  # created
                    row[4] or "未知"   # updated
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def show_mappings_by_type(self, external_type: str, limit: int = 20):
        """按类型显示映射"""
        print(f"\n=== {external_type} 类型映射 (前 {limit} 条) ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT external_id, paper_id, 
                       datetime(created_at, 'unixepoch') as created,
                       datetime(updated_at, 'unixepoch') as updated
                FROM external_id_mappings 
                WHERE external_type = ? 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (external_type, limit))
            
            results = cursor.fetchall()
            
            if not results:
                print(f"❌ 没有找到 {external_type} 类型的映射")
                return
            
            headers = ["外部ID", "论文ID", "创建时间", "更新时间"]
            table_data = []
            for row in results:
                # 截断长ID以便显示
                external_id = row[0][:60] + "..." if len(row[0]) > 60 else row[0]
                paper_id = row[1][:40] + "..." if len(row[1]) > 40 else row[1]
                
                table_data.append([
                    external_id,
                    paper_id,
                    row[2] or "未知",
                    row[3] or "未知"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def search_mapping(self, search_term: str, search_type: str = "all"):
        """搜索映射"""
        print(f"\n=== 搜索结果: '{search_term}' ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if search_type == "external_id":
                query = """
                    SELECT external_type, external_id, paper_id, 
                           datetime(updated_at, 'unixepoch') as updated
                    FROM external_id_mappings 
                    WHERE external_id LIKE ? 
                    ORDER BY updated_at DESC 
                    LIMIT 50
                """
                params = (f"%{search_term}%",)
            elif search_type == "paper_id":
                query = """
                    SELECT external_type, external_id, paper_id, 
                           datetime(updated_at, 'unixepoch') as updated
                    FROM external_id_mappings 
                    WHERE paper_id LIKE ? 
                    ORDER BY updated_at DESC 
                    LIMIT 50
                """
                params = (f"%{search_term}%",)
            else:  # all
                query = """
                    SELECT external_type, external_id, paper_id, 
                           datetime(updated_at, 'unixepoch') as updated
                    FROM external_id_mappings 
                    WHERE external_id LIKE ? OR paper_id LIKE ? 
                    ORDER BY updated_at DESC 
                    LIMIT 50
                """
                params = (f"%{search_term}%", f"%{search_term}%")
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            if not results:
                print("❌ 没有找到匹配的记录")
                return
            
            print(f"✅ 找到 {len(results)} 条记录:")
            
            headers = ["类型", "外部ID", "论文ID", "更新时间"]
            table_data = []
            for row in results:
                # 截断长ID以便显示
                external_id = row[1][:50] + "..." if len(row[1]) > 50 else row[1]
                paper_id = row[2][:30] + "..." if len(row[2]) > 30 else row[2]
                
                table_data.append([
                    row[0],  # type
                    external_id,
                    paper_id,
                    row[3] or "未知"  # updated
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def show_paper_aliases(self, paper_id: str):
        """显示特定论文的所有别名"""
        print(f"\n=== 论文 {paper_id} 的所有别名 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT external_type, external_id, 
                       datetime(created_at, 'unixepoch') as created,
                       datetime(updated_at, 'unixepoch') as updated
                FROM external_id_mappings 
                WHERE paper_id = ? 
                ORDER BY external_type, updated_at DESC
            """, (paper_id,))
            
            results = cursor.fetchall()
            
            if not results:
                print("❌ 没有找到该论文的别名")
                return
            
            print(f"✅ 找到 {len(results)} 个别名:")
            
            headers = ["类型", "外部ID", "创建时间", "更新时间"]
            table_data = []
            for row in results:
                table_data.append([
                    row[0],  # type
                    row[1],  # external_id (完整显示)
                    row[2] or "未知",  # created
                    row[3] or "未知"   # updated
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def show_duplicate_aliases(self):
        """显示重复的别名（同一个外部ID映射到多个论文）"""
        print("\n=== 重复别名检查 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT external_type, external_id, COUNT(DISTINCT paper_id) as paper_count,
                       GROUP_CONCAT(DISTINCT paper_id) as paper_ids
                FROM external_id_mappings 
                GROUP BY external_type, external_id 
                HAVING COUNT(DISTINCT paper_id) > 1
                ORDER BY paper_count DESC
            """)
            
            results = cursor.fetchall()
            
            if not results:
                print("✅ 没有发现重复的别名")
                return
            
            print(f"⚠️  发现 {len(results)} 个重复别名:")
            
            headers = ["类型", "外部ID", "论文数", "论文IDs"]
            table_data = []
            for row in results:
                # 截断长ID以便显示
                external_id = row[1][:40] + "..." if len(row[1]) > 40 else row[1]
                paper_ids = row[3][:80] + "..." if len(row[3]) > 80 else row[3]
                
                table_data.append([
                    row[0],  # type
                    external_id,
                    row[2],  # paper_count
                    paper_ids
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def delete_paper_mappings(self, paper_id: str, confirm: bool = False):
        """删除特定论文的所有映射"""
        print(f"\n=== 删除论文 {paper_id} 的映射 ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 首先检查要删除的映射
            cursor.execute("""
                SELECT external_type, external_id, 
                       datetime(created_at, 'unixepoch') as created
                FROM external_id_mappings 
                WHERE paper_id = ? 
                ORDER BY external_type, created
            """, (paper_id,))
            
            results = cursor.fetchall()
            
            if not results:
                print("❌ 没有找到该论文的映射，无需删除")
                return False
            
            print(f"📋 将要删除 {len(results)} 个映射:")
            
            headers = ["类型", "外部ID", "创建时间"]
            table_data = []
            for row in results:
                table_data.append([
                    row[0],  # type
                    row[1],  # external_id
                    row[2] or "未知"  # created
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            # 确认删除
            if not confirm:
                print("\n⚠️  这是一个危险操作，将永久删除这些映射记录！")
                response = input("确认删除？请输入 'yes' 继续: ").strip().lower()
                if response != 'yes':
                    print("❌ 操作已取消")
                    return False
            
            # 执行删除
            cursor.execute("DELETE FROM external_id_mappings WHERE paper_id = ?", (paper_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ 成功删除 {deleted_count} 个映射记录")
            return True
    
    def delete_specific_mapping(self, external_id: str, external_type: str, confirm: bool = False):
        """删除特定的映射记录"""
        print(f"\n=== 删除映射 {external_type}:{external_id} ===")
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 首先检查要删除的映射
            cursor.execute("""
                SELECT paper_id, datetime(created_at, 'unixepoch') as created,
                       datetime(updated_at, 'unixepoch') as updated
                FROM external_id_mappings 
                WHERE external_id = ? AND external_type = ?
            """, (external_id, external_type))
            
            result = cursor.fetchone()
            
            if not result:
                print("❌ 没有找到该映射记录")
                return False
            
            print("📋 将要删除的映射:")
            print(f"  类型: {external_type}")
            print(f"  外部ID: {external_id}")
            print(f"  论文ID: {result[0]}")
            print(f"  创建时间: {result[1] or '未知'}")
            print(f"  更新时间: {result[2] or '未知'}")
            
            # 确认删除
            if not confirm:
                print("\n⚠️  这是一个危险操作，将永久删除这个映射记录！")
                response = input("确认删除？请输入 'yes' 继续: ").strip().lower()
                if response != 'yes':
                    print("❌ 操作已取消")
                    return False
            
            # 执行删除
            cursor.execute(
                "DELETE FROM external_id_mappings WHERE external_id = ? AND external_type = ?", 
                (external_id, external_type)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"✅ 成功删除映射记录")
            return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SQLite别名映射查看器")
    parser.add_argument(
        "--db", "-d", 
        default="data/external_id_mapping.db",
        help="SQLite数据库文件路径 (默认: data/external_id_mapping.db)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # info命令 - 显示表信息
    subparsers.add_parser("info", help="显示数据库表结构信息")
    
    # stats命令 - 显示统计信息
    subparsers.add_parser("stats", help="显示统计信息")
    
    # recent命令 - 显示最近的映射
    recent_parser = subparsers.add_parser("recent", help="显示最近的映射")
    recent_parser.add_argument("--limit", "-l", type=int, default=10, help="显示条数 (默认: 10)")
    
    # type命令 - 按类型显示映射
    type_parser = subparsers.add_parser("type", help="按类型显示映射")
    type_parser.add_argument("external_type", choices=EXTERNAL_ID_TYPES, help="外部ID类型")
    type_parser.add_argument("--limit", "-l", type=int, default=20, help="显示条数 (默认: 20)")
    
    # search命令 - 搜索映射
    search_parser = subparsers.add_parser("search", help="搜索映射")
    search_parser.add_argument("term", help="搜索关键词")
    search_parser.add_argument(
        "--type", "-t", 
        choices=["all", "external_id", "paper_id"], 
        default="all",
        help="搜索类型 (默认: all)"
    )
    
    # paper命令 - 显示论文的所有别名
    paper_parser = subparsers.add_parser("paper", help="显示论文的所有别名")
    paper_parser.add_argument("paper_id", help="论文ID")
    
    # duplicates命令 - 显示重复别名
    subparsers.add_parser("duplicates", help="检查重复别名")
    
    # delete-paper命令 - 删除论文的所有映射
    delete_paper_parser = subparsers.add_parser("delete-paper", help="删除论文的所有映射")
    delete_paper_parser.add_argument("paper_id", help="论文ID")
    delete_paper_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接删除")
    
    # delete-mapping命令 - 删除特定映射
    delete_mapping_parser = subparsers.add_parser("delete-mapping", help="删除特定映射")
    delete_mapping_parser.add_argument("external_type", choices=EXTERNAL_ID_TYPES, help="外部ID类型")
    delete_mapping_parser.add_argument("external_id", help="外部ID")
    delete_mapping_parser.add_argument("--yes", "-y", action="store_true", help="跳过确认直接删除")
    
    # all命令 - 显示所有信息
    subparsers.add_parser("all", help="显示所有信息 (info + stats + recent)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        viewer = SQLiteAliasViewer(args.db)
        
        print(f"🗃️  数据库: {args.db}")
        
        if args.command == "info":
            viewer.show_table_info()
        elif args.command == "stats":
            viewer.show_statistics()
        elif args.command == "recent":
            viewer.show_recent_mappings(args.limit)
        elif args.command == "type":
            viewer.show_mappings_by_type(args.external_type, args.limit)
        elif args.command == "search":
            viewer.search_mapping(args.term, args.type)
        elif args.command == "paper":
            viewer.show_paper_aliases(args.paper_id)
        elif args.command == "duplicates":
            viewer.show_duplicate_aliases()
        elif args.command == "delete-paper":
            viewer.delete_paper_mappings(args.paper_id, args.yes)
        elif args.command == "delete-mapping":
            viewer.delete_specific_mapping(args.external_id, args.external_type, args.yes)
        elif args.command == "all":
            viewer.show_table_info()
            viewer.show_statistics()
            viewer.show_recent_mappings(10)
            viewer.show_duplicate_aliases()
        
    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
