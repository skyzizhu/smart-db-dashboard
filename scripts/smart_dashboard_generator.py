#!/usr/bin/env python3
"""
智能数据看板生成器
集成数据库连接、查询解析、SQL生成和可视化
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import Counter
from smart_db_connector import SmartDBConnector
from nlp_query_parser import NLPQueryParser

class SmartDashboardGenerator:
    def __init__(self, config_file: str = "db_config.json"):
        """初始化智能看板生成器"""
        self.db = SmartDBConnector(config_file)
        self.parser = NLPQueryParser(self.db)
        self.template_path = "assets/enhanced_dashboard_template.html"
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """处理用户查询的完整流程"""
        print(f"🔍 处理查询: {user_query}")
        
        # 1. 尝试建立数据库连接（不主动发现表，表匹配时按需调用 SHOW TABLES）
        if not self.db.connect():
            return {
                "success": False,
                "error": "数据库连接失败，请检查配置",
                "type": "connection_error"
            }

        # 2. 解析查询并生成执行计划（优先使用 entity_config 映射，失败时再通过 SHOW TABLES 匹配）
        query_plan = self.parser.parse_query(user_query)
        
        if not query_plan["success"]:
            return query_plan
        
        print(f"📋 匹配到表: {query_plan['primary_table']}")
        print(f"🎯 查询意图: {query_plan['query_intent']}")
        
        # 4. 执行SQL查询
        sql_result = self.db.execute_query(query_plan["sql_query"])
        
        if not sql_result["success"]:
            return {
                "success": False,
                "error": f"SQL执行失败: {sql_result['error']}",
                "sql": query_plan["sql_query"],
                "type": "sql_error"
            }
        
        print(f"📊 查询结果: {sql_result['row_count']} 行")
        
        # 5. 组装完整结果
        start_time = datetime.now()
        result = {
            "success": True,
            "data": sql_result["data"],
            "columns": sql_result["columns"],
            "row_count": sql_result["row_count"],
            "query_plan": query_plan,
            "sql_query": query_plan["sql_query"],
            "chart_type": query_plan["chart_type"],
            "description": self._generate_description(user_query, query_plan, sql_result),
            "timestamp": datetime.now().isoformat(),
            "original_query": user_query,
            "matched_tables": query_plan["table_matches"],
            "query_time": f"{(datetime.now() - start_time).total_seconds():.2f}s"
        }

        # 6. 生成统计和图表数据
        result["stats"] = self._generate_stats(result)
        result["charts"] = self._generate_charts(result)

        # 7. 关闭数据库连接
        self.db.disconnect()

        return result
    
    def _generate_description(self, query: str, plan: Dict[str, Any], 
                          sql_result: Dict[str, Any]) -> str:
        """生成查询结果描述"""
        intent = plan.get("query_intent", {})
        table_name = plan["primary_table"]
        time_conditions = intent.get("time_conditions") or []
        time_desc = time_conditions[0]["description"] if time_conditions else ""

        def _with_time_suffix(text: str) -> str:
            if time_desc:
                return f"{text}（时间范围：{time_desc}）"
            return text
        
        # 根据查询类型生成描述
        if intent.get("count"):
            count_value = sql_result["data"][0].get("count_value", 0) if sql_result["data"] else 0
            return _with_time_suffix(f"{table_name}表中的记录数量: {count_value}")
        elif intent.get("sum"):
            sum_value = sql_result["data"][0].get("sum_value", 0) if sql_result["data"] else 0
            return _with_time_suffix(f"{table_name}表中指定字段的总和: {sum_value}")
        elif intent.get("avg"):
            avg_value = sql_result["data"][0].get("avg_value", 0) if sql_result["data"] else 0
            return _with_time_suffix(f"{table_name}表中指定字段的平均值: {avg_value}")
        else:
            return _with_time_suffix(f"查询结果: {sql_result['row_count']} 条记录")

    def _generate_stats(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """生成统计数据"""
        stats = {"list": []}
        data = result.get("data", [])

        if not data:
            return stats

        # 总记录数
        stats["list"].append({
            "label": "总记录数",
            "value": result.get("row_count", 0)
        })

        # 分析数据列，生成统计
        columns = result.get("columns", [])

        # 查找数值列进行统计
        numeric_columns = []
        for i, col in enumerate(columns):
            if data and len(data) > 0:
                val = data[0].get(i) if isinstance(data[0], dict) else data[0][i]
                if isinstance(val, (int, float)) and 'id' not in col.lower():
                    numeric_columns.append(col)

        # 为数值列生成统计
        for col in numeric_columns[:5]:  # 最多5个数值列
            values = []
            for row in data:
                val = row.get(col) if isinstance(row, dict) else row[columns.index(col)]
                if isinstance(val, (int, float)):
                    values.append(val)

            if values:
                avg_val = sum(values) / len(values)
                stats["list"].append({
                    "label": f"{col} (平均)",
                    "value": f"{avg_val:.2f}"
                })

        # 统计唯一值数量（适用于分类字段）
        for col in columns[:5]:  # 最多5个列
            if col in ['id', 'uuid', 'UUID']:
                continue

            unique_values = set()
            for row in data:
                val = row.get(col) if isinstance(row, dict) else row[columns.index(col)]
                if val is not None:
                    unique_values.add(str(val))

            if 1 < len(unique_values) <= 20:  # 只显示有意义的分类
                stats["list"].append({
                    "label": f"{col} (分类数)",
                    "value": len(unique_values)
                })

        return stats

    def _generate_charts(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成图表配置"""
        charts = []
        data = result.get("data", [])
        columns = result.get("columns", [])

        if not data:
            return charts

        # 1. 生成分类数据的柱状图/饼图
        for col in columns[:8]:  # 最多8个列
            # 统计该列的值分布
            counter = Counter()
            for row in data:
                val = row.get(col) if isinstance(row, dict) else row.get(columns.index(col))
                if val is not None:
                    counter[str(val)] += 1

            # 只显示有分类意义的列（2-15个类别）
            if 2 <= len(counter) <= 15 and col not in ['id', 'uuid', 'UUID']:
                # 生成饼图
                chart_data = {
                    "type": "doughnut",
                    "title": f"{col} 分布",
                    "data": {
                        "labels": list(counter.keys())[:10],
                        "datasets": [{
                            "data": list(counter.values())[:10],
                            "backgroundColor": [
                                '#667eea', '#764ba2', '#f093fb', '#4facfe',
                                '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                                '#a8edea', '#fed6e3'
                            ][:len(counter)]
                        }]
                    }
                }
                charts.append(chart_data)

                if len(charts) >= 3:  # 最多3个图表
                    break

        # 2. 如果有时间列，生成趋势图
        time_columns = ['time', 'date', 'created_at', 'register_time', 'usage_time', 'viewing_time']
        for col in columns:
            if any(tc in col.lower() for tc in time_columns):
                # 按时间分组统计
                time_counter = Counter()
                for row in data:
                    val = row.get(col) if isinstance(row, dict) else row.get(columns.index(col))
                    if val:
                        # 提取日期部分
                        if isinstance(val, str):
                            date_part = val.split(' ')[0][:10]
                            time_counter[date_part] += 1

                if len(time_counter) > 1:
                    sorted_times = sorted(time_counter.items())
                    chart_data = {
                        "type": "line",
                        "title": f"{col} 趋势",
                        "data": {
                            "labels": [t[0] for t in sorted_times[-30:]],  # 最近30个时间点
                            "datasets": [{
                                "label": "数量",
                                "data": [t[1] for t in sorted_times[-30:]],
                                "borderColor": "#667eea",
                                "backgroundColor": "rgba(102, 126, 234, 0.1)",
                                "fill": True,
                                "tension": 0.4
                            }]
                        }
                    }
                    charts.append(chart_data)
                    break

        return charts
    
    def generate_dashboard_html(self, query_result: Dict[str, Any]) -> str:
        """生成完整的HTML看板（使用增强模板）"""
        if not query_result.get("success"):
            return self._generate_error_page(query_result.get("error", "未知错误"))

        # 读取增强模板
        template_path = self.template_path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_template_path = os.path.join(os.path.dirname(script_dir), template_path)

        if not os.path.exists(full_template_path):
            return self._generate_error_page("模板文件不存在")

        try:
            with open(full_template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()

            # 准备数据
            columns = query_result.get("columns", [])
            data = query_result.get("data", [])

            # 转换数据格式（从 tuple 转为 dict）
            formatted_data = []
            for row in data:
                if isinstance(row, (tuple, list)):
                    row_dict = {}
                    for i, col in enumerate(columns):
                        if i < len(row):
                            val = row[i]
                            # 格式化时间
                            if hasattr(val, 'strftime'):
                                val = val.strftime('%Y-%m-%d %H:%M:%S')
                            row_dict[col] = val
                    formatted_data.append(row_dict)
                else:
                    formatted_data.append(row)

            # 自定义JSON编码器处理特殊数据类型
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    # 处理datetime对象
                    if hasattr(obj, 'strftime'):
                        return obj.strftime('%Y-%m-%d %H:%M:%S')
                    # 处理Decimal对象（MySQL数值类型）
                    if hasattr(obj, 'float'):
                        return float(obj)
                    # 处理bytes对象
                    if isinstance(obj, bytes):
                        return obj.decode('utf-8', errors='ignore')
                    return super().default(obj)

            # 替换模板占位符
            replacements = {
                "{{TITLE}}": f"数据看板 - {query_result.get('original_query', '')}",
                "{{QUERY_TITLE}}": f"📊 {query_result.get('original_query', '')}",
                "{{QUERY_DESCRIPTION}}": query_result.get("description", ""),
                "{{GENERATED_TIME}}": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "{{QUERY_TIME}}": query_result.get("query_time", "N/A"),
                "{{ROW_COUNT}}": str(query_result.get("row_count", 0)),
                "{{DATA_JSON}}": json.dumps({
                    "success": True,
                    "data": formatted_data,
                    "columns": columns,
                    "row_count": query_result.get("row_count", 0),
                    "stats": query_result.get("stats", {"list": []}),
                    "charts": query_result.get("charts", []),
                    "meta": {
                        "original_query": query_result.get("original_query", ""),
                        "sql": query_result.get("sql_query", ""),
                        "primary_table": query_result.get("query_plan", {}).get("primary_table"),
                        "time_conditions": query_result.get("query_plan", {}).get("query_intent", {}).get("time_conditions", []),
                    },
                }, ensure_ascii=False, indent=2, cls=DateTimeEncoder)
            }

            html_content = html_template
            for placeholder, value in replacements.items():
                html_content = html_content.replace(placeholder, value)

            return html_content

        except Exception as e:
            return self._generate_error_page(f"生成页面失败: {str(e)}")
    
    def _generate_data_injection(self, query_result: Dict[str, Any]) -> str:
        """生成数据注入脚本"""
        data_json = json.dumps(query_result, ensure_ascii=False, indent=2)
        
        return f"""
        <script>
            // 注入的查询数据和计划
            window.queryData = {data_json};
            window.originalQuery = "{query_result['original_query']}";
            
            // 重写dashboard.js中的数据获取逻辑
            if (typeof DashboardManager !== 'undefined') {{
                DashboardManager.prototype.callPythonScript = async function(action, params) {{
                    if (action === 'test_connection') {{
                        return {{success: true}};
                    }}
                    if (action === 'execute_query') {{
                        return window.queryData;
                    }}
                    throw new Error('未知的操作');
                }};
                
                // 初始化时自动显示数据
                document.addEventListener('DOMContentLoaded', () => {{
                    setTimeout(() => {{
                        if (window.queryData && window.queryData.success) {{
                            dashboard.renderDashboard(window.queryData);
                        }}
                    }}, 500);
                }});
            }}
        </script>
        """
    
    def _generate_error_page(self, error_message: str) -> str:
        """生成错误页面"""
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>查询错误</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }}
                .error-container {{
                    background: rgba(255, 255, 255, 0.95);
                    border-radius: 12px;
                    padding: 40px;
                    max-width: 500px;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                .error-icon {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .error-title {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 15px;
                }}
                .error-message {{
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 20px;
                }}
                .btn {{
                    padding: 12px 24px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }}
                .debug-info {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px;
                    margin-top: 20px;
                    text-align: left;
                    font-family: monospace;
                    font-size: 12px;
                    border: 1px solid #e9ecef;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">❌</div>
                <div class="error-title">查询处理失败</div>
                <div class="error-message">{error_message}</div>
                <a href="javascript:history.back()" class="btn">返回重试</a>
                <div class="debug-info">
                    <strong>调试信息:</strong><br>
                    时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                    请检查数据库配置和表结构是否正确
                </div>
            </div>
        </body>
        </html>
        """
    
    def create_dashboard(self, user_query: str, output_file: str = None, query_result: Dict[str, Any] = None) -> str:
        """创建完整的看板并保存到文件"""
        print(f"🚀 开始创建看板: {user_query}")

        # 处理查询（如未提供现成结果，则内部执行一次查询）
        if query_result is None:
            query_result = self.process_query(user_query)

        if not query_result["success"]:
            # 即使出错也要生成页面
            html_content = self.generate_dashboard_html(query_result)
        else:
            html_content = self.generate_dashboard_html(query_result)

        # 生成带时间戳的唯一文件名
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:23]  # 包含微秒确保唯一
            # 生成简短的查询摘要
            query_summary = "".join(c for c in user_query[:20] if c.isalnum() or c in ('-', '_'))
            output_file = f"dashboard_{query_summary}_{timestamp}.html"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            abs_path = os.path.abspath(output_file)
            print(f"✅ 看板已生成: {output_file}")
            print(f"📊 数据量: {query_result.get('row_count', 0)} 条")
            print(f"🌐 请在浏览器中打开查看: file://{abs_path}")

            # 自动在浏览器中打开（macOS）
            try:
                import subprocess
                subprocess.run(['open', abs_path], check=False)
            except:
                pass  # 如果不是 macOS 或打开失败，忽略错误

            return output_file

        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return None

def _check_entity_config(entity_config_path: str) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not os.path.exists(entity_config_path):
        warnings.append(f"找不到实体配置文件: {entity_config_path}")
        return False, errors, warnings

    try:
        with open(entity_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        errors.append(f"实体配置文件解析失败: {e}")
        return False, errors, warnings

    if not isinstance(cfg, dict):
        errors.append("实体配置文件不是有效的JSON对象")
        return False, errors, warnings

    entity_mappings = cfg.get("entity_mappings", {})
    time_field_mappings = cfg.get("time_field_mappings", {})

    if not isinstance(entity_mappings, dict):
        errors.append("entity_mappings 必须是对象")
    if not isinstance(time_field_mappings, dict):
        errors.append("time_field_mappings 必须是对象")

    flat_count = 0
    for category, entities in entity_mappings.items():
        if isinstance(category, str) and category.startswith("_"):
            continue
        if isinstance(entities, dict):
            flat_count += len(
                [k for k in entities.keys() if not (isinstance(k, str) and k.startswith("_"))]
            )

    if flat_count == 0:
        warnings.append("entity_mappings 中没有可用的实体映射，无法通过业务名称匹配表")

    return (not errors), errors, warnings


def main():
    """主函数 - 命令行使用"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="智能数据看板生成器")
    parser.add_argument("query", nargs="*", help="自然语言查询，例如: 今天的用户注册量")
    parser.add_argument("--check-config", action="store_true", help="检查 db_config.json 和 entity_config.json 配置并测试数据库连接")
    parser.add_argument("--db-config", default="db_config.json", help="数据库配置文件路径")
    parser.add_argument("--entity-config", default="entity_config.json", help="实体配置文件路径")
    parser.add_argument("--mode", choices=["dashboard", "sql", "json"], default="dashboard", help="输出模式: 仪表盘HTML / 仅SQL / 原始JSON结果")
    parser.add_argument("--output", help="输出HTML文件路径(仅 dashboard 模式有效)")

    args = parser.parse_args()

    if args.check_config:
        print("🧪 开始检查数据库配置与实体配置")
        db = SmartDBConnector(args.db_config)
        db_result = db.validate_config()

        if db_result["ok"]:
            print("✅ db_config.json 字段检查通过")
        else:
            print("❌ db_config.json 存在问题:")
            for e in db_result["errors"]:
                print(f"  - {e}")
        for w in db_result.get("warnings", []):
            print(f"⚠️ {w}")

        print("\n🧪 测试数据库连接...")
        if db.test_connection():
            print("✅ 数据库连接成功")
        else:
            print("❌ 数据库连接失败，请检查网络、防火墙以及账号密码")

        print("\n🧪 检查实体配置文件 entity_config.json")
        ok_entity, entity_errors, entity_warnings = _check_entity_config(args.entity_config)
        if ok_entity:
            print("✅ entity_config.json 基本结构检查通过")
        else:
            print("❌ entity_config.json 存在问题:")
            for e in entity_errors:
                print(f"  - {e}")
        for w in entity_warnings:
            print(f"⚠️ {w}")

        return

    if not args.query:
        parser.print_help()
        return

    user_query = " ".join(args.query)
    generator = SmartDashboardGenerator(args.db_config)

    if args.mode == "sql":
        plan = generator.parser.parse_query(user_query)
        if not plan.get("success"):
            print(f"❌ 解析失败: {plan.get('error', '未知错误')}")
            return
        print("📋 匹配到表:", plan.get("primary_table"))
        print("📌 生成的SQL:")
        print(plan.get("sql_query"))
        return

    if args.mode == "json":
        result = generator.process_query(user_query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # dashboard 模式：先查询出结果，再询问是否生成 HTML 看板
    result = generator.process_query(user_query)
    if not result.get("success"):
        print(f"❌ 查询失败: {result.get('error', '未知错误')}")

        def _ask_yes_no(prompt: str) -> bool:
            try:
                answer = input(prompt).strip().lower()
            except EOFError:
                return False
            return answer in ("y", "yes", "是", "好", "ok")

        if _ask_yes_no("是否生成错误HTML看板用于排查？(y/n): "):
            generator.create_dashboard(user_query, output_file=args.output, query_result=result)
        return

    # 查询成功时，先给出简要信息和SQL，再征询是否导出HTML
    plan = result.get("query_plan") or {}
    print("📋 匹配到表:", plan.get("primary_table"))
    print("📌 生成的SQL:")
    print(result.get("sql_query", ""))
    print("📊 结果行数:", result.get("row_count", 0))

    def _ask_yes_no(prompt: str) -> bool:
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            return False
        return answer in ("y", "yes", "是", "好", "ok")

    if _ask_yes_no("是否生成 HTML 数据看板？(y/n): "):
        generator.create_dashboard(user_query, output_file=args.output, query_result=result)
    else:
        print("已跳过 HTML 看板生成。")

if __name__ == "__main__":
    main()
