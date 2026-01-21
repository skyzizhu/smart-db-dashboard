# 智能数据库看板 - 用户配置指南

## 📖 概述

本配置指南帮助您自定义智能数据库看板系统，使其适应您的数据库结构和业务需求。

## 📁 配置文件位置

```
smart-db-dashboard/
├── entity_config.json       # 业务实体配置文件（可自定义）
├── db_config.json           # 数据库连接配置（必须配置）
└── scripts/
    └── nlp_query_parser.py  # 自动读取配置文件
```

## 🚀 快速开始

### 1. 配置数据库连接

编辑 `db_config.json`：

```json
{
  "host": "your_database_host",
  "port": 3306,
  "user": "your_username",
  "password": "your_password",
  "database": "your_database_name",
  "charset": "utf8mb4"
}
```

### 2. 配置业务实体映射

编辑 `entity_config.json`，添加您的表映射：

```json
{
  "entity_mappings": {
    "用户相关": {
      "用户表": "your_user_table",
      "会员表": "your_user_table"
    },
    "订单相关": {
      "订单表": "your_order_table",
      "销售表": "your_order_table"
    }
  }
}
```

### 3. 配置时间字段映射

告诉系统每个表应该使用哪个时间字段：

```json
{
  "time_field_mappings": {
    "your_user_table": "created_at",
    "your_order_table": "order_time",
    "your_log_table": "log_time"
  }
}
```

## 📋 配置文件详解

### entity_config.json 完整示例

```json
{
  "_comment": "智能数据库看板 - 业务实体配置文件",

  "entity_mappings": {
    "_comment": "业务名称 -> 实际表名",
    "_description": "支持多个业务名称指向同一个表",

    "用户信息": {
      "用户表": "tb_users",
      "注册表": "tb_users",
      "会员表": "tb_users"
    },

    "订单信息": {
      "订单表": "tb_orders",
      "销售表": "tb_orders",
      "交易表": "tb_orders"
    }
  },

  "time_field_mappings": {
    "_comment": "表名 -> 时间字段",

    "tb_users": "created_at",
    "tb_orders": "order_time"
  },

  "custom_query_patterns": {
    "_comment": "自定义关键词模式（高级）",

    "销售相关": {
      "销售": "(销售|订单|购买|支付)",
      "退款": "(退款|退货|取消)"
    }
  }
}
```

## 🎯 使用示例

配置完成后，您可以用自然语言查询：

```bash
# 使用配置的业务实体名称
"查询用户表的总数"
"订单表最近7天的数据"
"销售表过去一个月的统计"

# 系统会自动：
# 1. 识别"用户表" -> tb_users
# 2. 识别"订单表" -> tb_orders
# 3. 使用正确的时间字段（created_at / order_time）
```

## ⚙️ 配置项说明

### 1. entity_mappings（业务实体映射）

**作用**：将用户友好的名称映射到实际数据库表名

**格式**：
```json
{
  "分类名称（可选）": {
    "用户名称1": "实际表名",
    "用户名称2": "实际表名"
  }
}
```

**示例**：
```json
{
  "用户相关": {
    "用户表": "app_users",
    "注册表": "app_users",
    "会员": "app_users"
  }
}
```

### 2. time_field_mappings（时间字段映射）

**作用**：指定每个表应该使用哪个时间字段

**格式**：
```json
{
  "表名": "时间字段名"
}
```

**示例**：
```json
{
  "app_users": "created_at",
  "app_orders": "order_time",
  "app_logs": "timestamp"
}
```

### 3. custom_query_patterns（自定义查询模式）

**作用**：添加业务特定的关键词，提高识别准确度

**格式**：
```json
{
  "分类": {
    "模式名": "正则表达式"
  }
}
```

**示例**：
```json
{
  "电商": {
    "销售": "(销售|订单|购买|支付)",
    "退款": "(退款|退货|取消)"
  }
}
```

## 🔧 高级配置

### 支持的查询模式

系统默认支持以下查询模式：

| 类型 | 模式 | 示例 |
|------|------|------|
| 统计 | 多少、数量、总数 | "用户表有多少人" |
| 时间 | 今天、本周、本月 | "今天的订单量" |
| 灵活时间 | 最近X天/周/月 | "最近7天的数据" |
| 排序 | 最新、最早 | "最新的用户" |

### 时间范围表达

支持以下时间表达方式：

- `今天` / `今日`
- `昨天` / `昨日`
- `本周` / `这周`
- `上周` / `上一周`
- `本月` / `这个月`
- `上月` / `上个月`
- `最近X天` / `过去X天` / `前X天`
- `最近X周` / `过去X周`
- `最近X月` / `过去X月`

## 🐛 故障排除

### 问题1：配置文件不生效

**检查**：
1. 配置文件是否在正确位置：`smart-db-dashboard/entity_config.json`
2. JSON 格式是否正确（可用在线工具验证）
3. 是否有中文编码问题（使用 UTF-8 编码）

### 问题2：无法识别业务实体

**解决**：
1. 检查 `entity_mappings` 中是否添加了对应的映射
2. 查询语句中的名称是否与配置完全一致
3. 查看控制台输出的警告信息

### 问题3：时间条件不正确

**解决**：
1. 确认 `time_field_mappings` 中配置了正确的表名和字段名
2. 检查表中是否存在该时间字段

## 📚 配置模板

### 电商系统配置模板

```json
{
  "entity_mappings": {
    "用户": {
      "用户表": "tb_users",
      "会员表": "tb_users",
      "客户表": "tb_users"
    },
    "订单": {
      "订单表": "tb_orders",
      "销售表": "tb_orders",
      "交易表": "tb_orders"
    },
    "商品": {
      "商品表": "tb_products",
      "产品表": "tb_products",
      "库存表": "tb_products"
    }
  },
  "time_field_mappings": {
    "tb_users": "created_at",
    "tb_orders": "order_time",
    "tb_products": "created_at"
  }
}
```

### 内容管理系统配置模板

```json
{
  "entity_mappings": {
    "内容": {
      "文章表": "tb_articles",
      "内容表": "tb_articles",
      "帖子表": "tb_posts"
    },
    "用户": {
      "用户表": "tb_users",
      "作者表": "tb_users"
    },
    "评论": {
      "评论表": "tb_comments",
      "留言表": "tb_comments"
    }
  },
  "time_field_mappings": {
    "tb_articles": "publish_time",
    "tb_users": "created_at",
    "tb_comments": "comment_time"
  }
}
```

## 💡 最佳实践

1. **命名规范**
   - 使用简单、直观的业务名称
   - 保持命名一致性

2. **分类组织**
   - 将相关的映射放在同一个分类下
   - 使用有意义的分类名称

3. **逐步扩展**
   - 先配置常用的表
   - 根据使用情况逐步添加更多映射

4. **测试验证**
   - 配置后测试查询是否正常
   - 检查生成的 SQL 是否正确

## 📞 技术支持

如有问题，请检查：
1. 配置文件 JSON 格式是否正确
2. 数据库连接是否正常
3. 表名和字段名是否准确
