# 智能数据库看板生成器

> 用自然语言查询 MySQL 数据库，自动生成可视化 HTML 看板

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/mysql-5.7+-orange.svg)](https://www.mysql.com/)
[![Version](https://img.shields.io/badge/version-3.0-brightgreen.svg)](https://github.com/skyzizhu/smart-db-dashboard/releases)

---

## ✨ 特性

- 🗣️ **自然语言查询** - 用中文描述查询需求，系统自动生成 SQL
- 🎯 **智能表匹配** - 自动发现数据库表，智能匹配查询意图
- 📊 **自动可视化** - 根据数据类型自动生成图表（饼图、折线图等）
- 📄 **HTML 看板导出** - 生成独立的 HTML 文件，支持分页浏览
- ⚙️ **可配置化** - 支持自定义业务实体映射和查询模式
- 🚀 **开箱即用** - 简单配置即可使用

---

## 📸 看板预览

生成的看板包含：

- 📈 **统计卡片** - 总记录数、平均值、分类统计等
- 📊 **数据图表** - 饼图展示分布、折线图展示趋势
- 📋 **分页列表** - 支持翻页浏览所有数据
- 📱 **响应式设计** - 适配桌面、平板、手机

---

## 👥 适用人群

### 🎯 产品经理

这是一个专为产品经理设计的 **产品经理 Skill**，让你无需 SQL 知识也能轻松查看和分析用户数据：

**用户数据分析**
- 查看用户总数、注册量、活跃用户统计
- 分析用户增长趋势和留存情况
- 了解用户分布和用户画像

**业务数据监控**
- 实时查看核心业务指标（KPI）
- 监控功能使用情况和用户行为
- 分析销售数据和订单趋势

**快速决策支持**
- 无需等待数据报表，即时获取数据
- 自动生成可视化图表，直观展示数据
- 支持导出 HTML 看板，方便分享给团队

**使用场景示例**
```
产品经理: 查看最近一周的用户注册趋势
产品经理: 分析用户设备类型分布
产品经理: 统计本月新增用户数量
产品经理: 查看某个功能的使用情况
```

### 👨‍💻 数据分析师

快速探索数据库，生成临时报表和可视化图表

### 🛠️ 开发人员

调试数据问题，验证数据逻辑，快速生成测试数据看板

---

## 🔧 环境要求

### 必需软件

| 软件 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | 3.7 或更高版本 | 核心运行环境 |
| **MySQL** | 5.7 或更高版本 | 数据库服务器 |
| **Claude Code** | 最新版本 | IDE集成支持（可选） |

### Python 依赖包

```bash
pip install mysql-connector-python
```

---

## 🚀 安装到本地 IDE

### 方法一：下载 Skill 文件安装

1. **下载 Skill 文件**
   ```bash
   # 克隆仓库
   git clone https://github.com/skyzizhu/smart-db-dashboard.git
   cd smart-db-dashboard
   ```

2. **创建 Skill 配置文件**
   ```bash
   # 将项目目录配置为 skill
   # 在 Claude Code 的 skills 配置中添加此路径
   ```

3. **配置数据库连接**
   ```bash
   # 复制配置模板
   cp db_config.json.template db_config.json

   # 编辑配置文件，填入你的数据库信息
   vim db_config.json
   ```

   ```json
   {
     "host": "your_database_host",
     "port": 3306,
     "user": "your_username",
     "password": "your_password",
     "database": "your_database",
     "charset": "utf8mb4"
   }
   ```

4. **在 IDE 中使用**

   安装完成后，直接在 Claude Code 中对话：

   ```
   用户: 查询用户表的总数
   Claude: [自动调用 smart-db-dashboard skill 生成看板]
   ```

### 方法二：直接使用 Python

如果不想安装到 IDE，也可以直接用 Python 运行：

```bash
# 安装依赖
pip install mysql-connector-python

# 运行查询
python scripts/smart_dashboard_generator.py "查询用户表的总数"
```

---

## 💡 使用示例

### 统计查询

```
用户: 查询用户表有多少人
用户: 今天的注册量是多少
用户: 订单表的平均销售额
```

### 时间范围查询

```
用户: 最近7天的用户注册量
用户: 使用表最近3天的数据
用户: 订单表本月的销售总额
```

### 列表查询

```
用户: 显示用户表最新的100条记录
用户: 查看订单表的销售详情
```

---

## 📂 项目结构

```
smart-db-dashboard/
├── assets/                           # 前端资源
│   ├── enhanced_dashboard_template.html  # 增强看板模板
│   └── dashboard.js                  # 交互脚本
├── scripts/                          # 核心脚本
│   ├── smart_db_connector.py        # 数据库连接器
│   ├── nlp_query_parser.py          # NLP 解析器
│   └── smart_dashboard_generator.py  # 看板生成器
├── entity_config.json                # 业务实体配置
├── db_config.json.template          # 数据库配置模板
├── CONFIG_GUIDE.md                  # 配置指南
├── README.md                        # 项目说明
├── SKILL.md                         # Skill 文档
└── LICENSE                          # 开源协议
```

---

## 📖 配置说明

### 业务实体映射

将用户友好的业务名称映射到实际数据库表名：

```json
{
  "entity_mappings": {
    "用户相关": {
      "用户表": "tb_users",
      "注册表": "tb_users",
      "会员表": "tb_users"
    },
    "订单相关": {
      "订单表": "tb_orders",
      "销售表": "tb_orders"
    }
  }
}
```

### 时间字段映射

指定每个表应该使用的时间字段：

```json
{
  "time_field_mappings": {
    "tb_users": "created_at",
    "tb_orders": "order_time"
  }
}
```

**详细配置请参考 [CONFIG_GUIDE.md](CONFIG_GUIDE.md)**

---

## 🎯 支持的查询模式

| 类型 | 示例 |
|------|------|
| 统计 | "用户表有多少人"、"订单表总数" |
| 时间范围 | "最近7天"、"本月"、"最近3个月" |
| 列表 | "显示最新的100条用户" |
| 趋势 | "最近一周的注册趋势" |

---

## 🎨 生成的看板功能

| 功能 | 说明 |
|------|------|
| **统计卡片** | 总记录数、平均值、分类数等 |
| **饼图** | 分类数据分布（如设备类型） |
| **折线图** | 时间趋势分析 |
| **分页列表** | 每页 20 条，支持翻页 |
| **自动刷新** | macOS 系统自动在浏览器打开 |

---

## 🔧 技术栈

- **Python 3.7+** - 核心逻辑
- **MySQL 5.7+** - 数据库支持
- **Chart.js 4.4** - 图表库
- **JavaScript ES6** - 前端交互

---

## 📋 版本历史

### v3.0 (2025-01-21)
- ✨ 新增自动 HTML 看板生成
- ✨ 新增数据图表（饼图、折线图）
- ✨ 新增统计卡片
- ✨ 新增分页列表功能
- ✨ 新增唯一文件命名
- ✨ 新增自动浏览器预览

### v2.0 (2025-01-20)
- ✨ 业务实体映射
- ✨ 灵活时间范围
- ✨ 可配置化支持

### v1.0 (2025-01-19)
- ✨ 初始版本
- ✨ 自然语言查询
- ✨ 智能表匹配

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/skyzizhu/smart-db-dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/skyzizhu/smart-db-dashboard/discussions)

---

## ⭐ Star History

如果这个项目对你有帮助，请给个 Star 支持！

---

**Made with ❤️ by Smart Dashboard Team**
