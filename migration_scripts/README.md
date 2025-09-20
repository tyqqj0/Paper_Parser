# 数据迁移脚本

## 外部ID映射迁移

### 概述
`migrate_external_ids.py` 脚本用于将现有的外部ID映射数据从Redis和Neo4j迁移到统一的SQLite数据库中。

### 迁移内容
- **Redis映射**：DOI、ArXiv、CorpusId等键值对映射
- **Neo4j属性**：论文节点的外部ID属性（doi, arxivId, corpusId等）

### 使用方法

#### 1. 运行迁移脚本
```bash
cd Paper_Parser
python migrations/migrate_external_ids.py
```

#### 2. 检查迁移日志
```bash
tail -f migration.log
```

### 迁移流程

1. **初始化**：创建SQLite数据库和映射表
2. **Redis迁移**：
   - 扫描 `doi:*` 键
   - 扫描 `arxiv:*` 键  
   - 扫描 `corpus:*` 键
3. **Neo4j迁移**：
   - 查询所有论文节点
   - 提取各种外部ID属性
4. **验证**：随机抽样验证映射正确性
5. **报告**：生成详细的迁移统计报告
6. **清理**（可选）：删除Redis中的旧映射键

### 安全特性

- **幂等性**：可以重复运行，不会产生重复数据
- **事务性**：每个映射的添加都是原子操作
- **验证**：迁移后自动验证数据完整性
- **日志**：详细的操作日志和错误记录
- **确认清理**：旧数据清理需要手动确认

### 预期结果

迁移完成后，您将得到：
- 统一的外部ID映射数据库 `external_id_mappings.db`
- 详细的迁移日志 `migration.log`
- 各类型映射的统计信息
- 数据完整性验证结果

### 故障排除

#### 常见问题

1. **数据库锁定**
   ```
   解决方案：确保没有其他进程在使用数据库文件
   ```

2. **Redis连接失败**
   ```
   解决方案：检查Redis服务状态和配置
   ```

3. **Neo4j连接失败**
   ```
   解决方案：检查Neo4j服务状态和认证信息
   ```

#### 重新运行迁移

如果迁移失败，可以：
1. 删除 `external_id_mappings.db` 文件
2. 重新运行迁移脚本
3. 检查错误日志并修复问题

### 性能说明

- **Redis迁移**：通常很快，取决于键的数量
- **Neo4j迁移**：可能较慢，取决于论文节点数量
- **内存使用**：脚本会在内存中缓存映射关系以检测重复

### 数据备份建议

在运行迁移之前，建议：
1. 备份Redis数据：`redis-cli BGSAVE`
2. 备份Neo4j数据：使用Neo4j的备份工具
3. 记录当前的映射统计信息

### 迁移后验证

迁移完成后，可以通过以下方式验证：

```python
from app.services.external_id_mapping import external_id_mapping

# 检查特定映射
paper_id = await external_id_mapping.get_paper_id("10.1038/nature12373", "DOI")
print(f"DOI映射结果: {paper_id}")

# 统计各类型数量
for ext_type in ExternalIdTypes.ALL_TYPES:
    mappings = await external_id_mapping.get_mappings_by_type(ext_type, limit=1)
    print(f"{ext_type}: {len(mappings)}条")
```
