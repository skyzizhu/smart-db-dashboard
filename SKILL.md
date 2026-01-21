---
name: smart-db-dashboard
description: Intelligent database query and dashboard generation system with automatic table discovery, natural language parsing, smart SQL generation, and multi-table join support. Use when Claude needs to connect to databases, discover tables automatically, match user queries to table structures, generate intelligent SQL queries, create dynamic data visualizations, or process database information with smart analysis.
---

# 智能数据库看板生成器

## 概述

智能数据库看板生成器提供完全自动化的数据库查询和可视化解决方案，支持表发现、自然语言理解、智能SQL生成和多表联查。

## 核心功能

### 1. 自动表发现和匹配
- 执行 `SHOW TABLES` 自动发现所有表
- 基于表名、列名和内容进行智能匹配
- 支持模糊匹配和关键词关联

### 2. 自然语言查询解析
- 解析用户中文查询意图
- 自动识别统计、排序、时间范围等条件
- 智能生成对应的SQL语句
- **新增**：业务实体映射（启动表、注册表、使用表等）
- **新增**：灵活时间范围（最近X天/周/月）

### 3. 智能SQL生成
- 根据匹配的表生成查询语句
- 支持聚合函数、条件过滤、排序分页
- 自动优化查询性能

### 4. 动态看板生成
- 根据查询结果选择最佳展示方式
- 支持单值、表格、图表等多种形式
- 包含查询分析和调试信息

## 使用流程

### 步骤1：配置数据库连接
编辑 `db_config.json` 文件：
```json
{
  "host": "localhost",
  "port": 3306,
  "user": "your_username",
  "password": "your_password",
  "database": "your_database",
  "charset": "utf8mb4"
}
```

### 步骤2：配置业务实体映射（可选）
编辑 `entity_config.json` 文件，将您的业务名称映射到实际表名：
```json
{
  "entity_mappings": {
    "用户相关": {
      "用户表": "your_user_table",
      "注册表": "your_user_table"
    },
    "订单相关": {
      "订单表": "your_order_table",
      "销售表": "your_order_table"
    }
  },
  "time_field_mappings": {
    "your_user_table": "created_at",
    "your_order_table": "order_time"
  }
}
```

**详细配置说明请参考 `CONFIG_GUIDE.md`**

### 步骤3：自然语言查询
支持多种查询模式：

**统计查询**：
- "查询用户总数"
- "今天的注册量有多少"
- "计算总销售额"

**列表查询**：
- "显示用户列表"
- "查看最新的订单"
- "活跃用户分页显示"

**趋势分析**：
- "最近7天的注册趋势"
- "本月的数据变化"
- "用户增长情况"

**业务实体查询**（新增）：
- "查询启动表中的用户条目"
- "注册表中有多少个用户"
- "使用表最近一周的数据"

**灵活时间范围**（新增）：
- "最近3天的注册量"
- "过去2周的使用情况"
- "前一个月的活跃用户"

### 步骤4：生成看板
```python
from scripts.smart_dashboard_generator import SmartDashboardGenerator

generator = SmartDashboardGenerator()
generator.create_dashboard("查询启动APP的用户数量")
```

## 智能匹配算法

### 表匹配规则
1. **直接匹配**：表名关键词直接匹配
2. **列名匹配**：根据查询中的字段匹配列
3. **语义关联**：基于业务含义的智能关联
4. **模糊匹配**：使用相似度算法

### 查询意图识别
- **统计类**：多少、总数、平均、最大、最小
- **时间类**：今天、最近、本周、本月、上周、上月
- **灵活时间**：最近X天/周/月、过去X天/周/月、前X天/周/月
- **排序类**：最新、最早、倒序
- **展示类**：列表、趋势、对比

### 业务实体映射（新增）
支持用户友好的业务实体名称自动映射到实际表名：

| 业务名称 | 实际表名 |
|---------|---------|
| 用户表/注册表 | yt_user_info_tb |
| 启动表/启动信息表 | yt_launchapp_info_tb |
| 使用表/功能使用表 | yt_funcuse_info_tb |
| 来源表/渠道表 | yt_usersource_info_tb |
| 埋点表 | yt_burial_point_tb |

### 时间字段映射（新增）
不同表自动使用对应的时间字段：

| 表名 | 时间字段 |
|------|---------|
| yt_user_info_tb | register_time |
| yt_launchapp_info_tb | viewing_time |
| yt_funcuse_info_tb | usage_time |
| yt_usersource_info_tb | created_at |
| yt_burial_point_tb | created_at |

## 多表联查支持

### 自动发现关联关系
- 识别共同字段作为连接条件
- 分析主外键关系
- 生成合理的JOIN语句

### 联查场景示例
```python
# 用户及其订单信息
"用户和他们的订单列表"

# 产品销售统计  
"产品的销售情况统计"

# 多维度分析
"不同地区用户的购买行为"
```

## 生成的看板特性

### 响应式设计
- 适配桌面、平板、手机
- 自适应布局和字体大小
- 触摸友好的交互

### 多种图表类型
- **单值卡片**：关键指标展示
- **数据表格**：详细列表查看
- **折线图**：时间趋势分析  
- **柱状图**：分类对比展示

### 调试信息
- 显示匹配的表和分数
- 展示生成的SQL语句
- 查询执行结果分析

## 资源结构

### scripts/
核心Python脚本，提供智能数据库功能：

- `smart_db_connector.py` - 智能数据库连接器，自动发现表和匹配
- `nlp_query_parser.py` - 自然语言查询解析器，识别查询意图
- `smart_dashboard_generator.py` - 看板生成器，集成所有功能

### assets/
前端模板和资源文件：

- `dashboard_template.html` - 响应式HTML模板
- `dashboard.js` - 交互式JavaScript逻辑

### references/
文档和参考资料目录，用于扩展功能。

## 高级功能

### 查询优化
- 自动添加LIMIT避免大查询
- 智能选择索引列进行排序
- 缓存表结构信息

### 错误处理
- 数据库连接失败处理
- SQL执行错误提示
- 查询解析失败建议

### 扩展性
- 易于添加新的查询模式
- 支持自定义匹配规则
- 可扩展的图表类型

## 使用示例

### 命令行使用
```bash
python scripts/smart_dashboard_generator.py "今天的用户注册量"
```

### Python代码使用
```python
from scripts.smart_dashboard_generator import SmartDashboardGenerator

generator = SmartDashboardGenerator()

# 处理查询
result = generator.process_query("查询活跃用户数量")
print(f"匹配的表: {result['query_plan']['primary_table']}")
print(f"生成的SQL: {result['query_plan']['sql_query']}")

# 生成看板
dashboard_file = generator.create_dashboard("查询订单总数")
```

## 技术特点

- **零配置启动**：自动发现表结构
- **智能解析**：支持自然语言查询
- **安全可靠**：SQL注入防护和错误处理
- **高性能**：查询优化和结果缓存
- **可扩展**：模块化设计易于扩展

## 依赖要求

```bash
pip install mysql-connector-python
```

## 浏览器兼容性

- Chrome/Edge 88+
- Firefox 85+
- Safari 14+
- 支持所有现代浏览器的ES6特性