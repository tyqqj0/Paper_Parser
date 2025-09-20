# SQLite别名映射查看器使用说明

这个脚本用于查看和分析SQLite数据库中的外部ID到论文ID的映射关系。

## 功能特性

- 📋 查看数据库表结构和索引信息
- 📊 显示详细的统计信息
- 🔍 按类型查看映射数据
- 🔎 搜索特定的映射记录
- 📄 查看单个论文的所有别名
- ⚠️ 检测重复的别名映射
- 🕒 显示最近的映射记录
- 🗑️ 删除论文映射和特定映射记录

## 安装依赖

```bash
pip install tabulate
```

## 基本使用

### 1. 查看帮助信息
```bash
python3 scripts/sqlite_alias_viewer.py --help
```

### 2. 查看所有信息（推荐首次使用）
```bash
python3 scripts/sqlite_alias_viewer.py all
```

### 3. 查看数据库表结构
```bash
python3 scripts/sqlite_alias_viewer.py info
```

### 4. 查看统计信息
```bash
python3 scripts/sqlite_alias_viewer.py stats
```

## 高级功能

### 按类型查看映射
```bash
# 查看DOI类型的映射
python3 scripts/sqlite_alias_viewer.py type DOI

# 查看ArXiv类型的映射
python3 scripts/sqlite_alias_viewer.py type ArXiv

# 支持的类型：DOI, ArXiv, CorpusId, MAG, ACL, PMID, PMCID, URL, TITLE_NORM, DBLP
```

### 搜索映射
```bash
# 搜索包含特定关键词的记录（在外部ID和论文ID中搜索）
python3 scripts/sqlite_alias_viewer.py search "10.1038"

# 只在外部ID中搜索
python3 scripts/sqlite_alias_viewer.py search "arxiv" --type external_id

# 只在论文ID中搜索
python3 scripts/sqlite_alias_viewer.py search "649def34" --type paper_id
```

### 查看论文的所有别名
```bash
# 查看特定论文的所有别名
python3 scripts/sqlite_alias_viewer.py paper "649def34f8be52c8b66281af98ae884c09aef38b"
```

### 查看最近的映射
```bash
# 查看最近10条映射（默认）
python3 scripts/sqlite_alias_viewer.py recent

# 查看最近50条映射
python3 scripts/sqlite_alias_viewer.py recent --limit 50
```

### 检查重复别名
```bash
# 检查是否有重复的别名（同一个外部ID映射到多个论文）
python3 scripts/sqlite_alias_viewer.py duplicates
```

### 删除映射（危险操作）
```bash
# 删除特定论文的所有映射
python3 scripts/sqlite_alias_viewer.py delete-paper "649def34f8be52c8b66281af98ae884c09aef38b"

# 删除特定的映射记录
python3 scripts/sqlite_alias_viewer.py delete-mapping DOI "10.1038/nature14539"

# 跳过确认直接删除（慎用！）
python3 scripts/sqlite_alias_viewer.py delete-paper "649def34f8be52c8b66281af98ae884c09aef38b" --yes
python3 scripts/sqlite_alias_viewer.py delete-mapping URL "https://example.com/paper" --yes
```

## 自定义数据库路径

如果数据库文件不在默认位置，可以指定路径：

```bash
python3 scripts/sqlite_alias_viewer.py --db /path/to/your/database.db all
```

## 输出示例

### 统计信息示例
```
=== 统计信息 ===
📊 总映射数: 10
📄 唯一论文数: 4
📈 平均别名数: 2.50

📋 按类型统计:
+----------+--------+--------+
| 类型     |   数量 | 占比   |
+==========+========+========+
| DOI      |      3 | 30.0%  |
+----------+--------+--------+
| URL      |      2 | 20.0%  |
+----------+--------+--------+
| ACL      |      1 | 10.0%  |
+----------+--------+--------+
```

### 论文别名示例
```
=== 论文 649def34f8be52c8b66281af98ae884c09aef38b 的所有别名 ===
✅ 找到 7 个别名:
+----------+----------------------------+
| 类型     | 外部ID                     |
+==========+============================+
| DOI      | 10.1038/nature14539        |
+----------+----------------------------+
| ACL      | P17-1001                   |
+----------+----------------------------+
| PMID     | 26017442                   |
+----------+----------------------------+
```

## 数据库结构

别名映射表 `external_id_mappings` 包含以下字段：

- `external_id` (TEXT, 主键): 外部标识符
- `external_type` (TEXT, 主键): 外部标识符类型
- `paper_id` (TEXT): 论文ID
- `created_at` (INTEGER): 创建时间戳
- `updated_at` (INTEGER): 更新时间戳

## 支持的外部ID类型

- **DOI**: Digital Object Identifier
- **ArXiv**: ArXiv预印本ID
- **CorpusId**: Semantic Scholar语料库ID
- **MAG**: Microsoft Academic Graph ID
- **ACL**: ACL Anthology ID
- **PMID**: PubMed ID
- **PMCID**: PubMed Central ID
- **URL**: 论文URL
- **TITLE_NORM**: 标准化标题
- **DBLP**: DBLP ID

## 注意事项

1. 数据库路径默认为 `data/external_id_mapping.db`
2. 长ID在表格中会被截断以便显示，但搜索功能仍然使用完整ID
3. 时间戳显示为本地时间格式
4. 脚本自动检测并处理数据库连接问题
5. **删除操作是不可逆的危险操作**，请谨慎使用
6. 删除前会显示将要删除的记录，需要输入 'yes' 确认，或使用 `--yes` 参数跳过确认
