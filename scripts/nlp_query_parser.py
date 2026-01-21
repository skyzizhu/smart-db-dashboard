#!/usr/bin/env python3
"""
自然语言查询解析器和SQL生成器
支持智能表匹配、多表联查规划和自动SQL生成
"""

import re
import json
import os
from typing import Dict, List, Any, Tuple, Optional
from difflib import SequenceMatcher
from smart_db_connector import SmartDBConnector

class NLPQueryParser:
    def __init__(self, db_connector: SmartDBConnector, config_file: str = None):
        self.db = db_connector

        # 加载配置文件
        self.config = self._load_config(config_file)

        # 从配置文件获取映射表
        self.entity_mappings = self._flatten_entity_mappings(self.config.get('entity_mappings', {}))
        self.time_field_mappings = self._filter_comment_fields(self.config.get('time_field_mappings', {}))

        # 合并自定义查询模式
        custom_patterns = self.config.get('custom_query_patterns', {}).get('examples', {})
        self.query_patterns = self._get_default_patterns()
        self.query_patterns.update(custom_patterns)

    def _filter_comment_fields(self, mappings: Dict) -> Dict[str, str]:
        """过滤掉注释字段（以_开头的字段）"""
        return {k: v for k, v in mappings.items() if not k.startswith('_')}

    def _load_config(self, config_file: str = None) -> Dict:
        """加载配置文件"""
        if config_file is None:
            # 默认配置文件路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(os.path.dirname(script_dir), 'entity_config.json')

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {config_file}: {e}")
                print("使用默认配置")

        # 返回空配置（使用内置默认值）
        return {}

    def _flatten_entity_mappings(self, mappings: Dict) -> Dict[str, str]:
        """将嵌套的实体映射展平为一维字典"""
        flat_mappings = {}
        for category, entities in mappings.items():
            if category.startswith('_'):
                continue  # 跳过注释字段
            if isinstance(entities, dict):
                for entity_name, table_name in entities.items():
                    flat_mappings[entity_name] = table_name
        return flat_mappings

    def _get_default_patterns(self) -> Dict[str, str]:
        """获取默认的查询模式"""
        return {
            # 统计查询模式
            'count': r'(多少|几个|数量|总数|统计)',
            'sum': r'(总和|总量|总计|累计)',
            'avg': r'(平均|均值)',
            'max': r'(最高|最大|最多)',
            'min': r'(最低|最小|最少)',

            # 分组统计模式
            'group_by': r'(各个|每个|按.*分组|分组.*统计|分别统计|.*的(使用|统计|情况))',

            # 灵活时间范围模式
            'last_days': r'(最近|过去|前)(\d+)(天|日)',
            'last_weeks': r'(最近|过去|前)(\d+)(周|星期)',
            'last_months': r'(最近|过去|前)(\d+)(个月?|月)',

            # 时间相关模式
            'today': r'(今天|今日)',
            'yesterday': r'(昨天|昨日)',
            'this_week': r'(这周|本周)',
            'last_week': r'(上周|上一周)',
            'this_month': r'(这个月|本月)',
            'last_month': r'(上个月|上月)',
            'this_year': r'(今年|本年)',

            # 排序模式
            'order_desc': r'(最新|最近|倒序)',
            'order_asc': r'(最早|最旧|正序)',

            # 分页模式
            'pagination': r'(分页|前\d+个|第\d+页)',

            # 业务实体模式
            'user': r'(用户|会员|客户)',
            'order': r'(订单|订单)',
            'product': r'(商品|产品)',
            'app': r'(app|应用)',
            'launch': r'(启动|打开|使用)',
            'register': r'(注册|注册|新用户)',
            'active': r'(活跃|登录|在线)',
        }
    
    def _map_entity_to_table(self, query: str) -> Optional[str]:
        """将业务实体名称映射到实际表名"""
        for entity_name, table_name in self.entity_mappings.items():
            if entity_name in query:
                return table_name
        return None

    def parse_query(self, user_query: str) -> Dict[str, Any]:
        """解析用户查询并生成执行计划"""
        # 0. 优先检查业务实体映射
        mapped_table = self._map_entity_to_table(user_query)
        if mapped_table:
            # 使用映射的表名，直接构造匹配结果
            table_matches = [(mapped_table, 1.0)]
        else:
            # 1. 发现并匹配表
            table_matches = self.db.match_tables(user_query)

        if not table_matches:
            return {
                "success": False,
                "error": "无法找到匹配的数据表",
                "suggestion": "请检查查询内容，尝试使用更明确的表名关键词"
            }
        
        # 2. 选择主表
        primary_table, match_score = table_matches[0]
        
        # 3. 获取主表结构
        table_info = self.db.get_table_structure(primary_table)
        
        # 4. 解析查询意图
        query_intent = self._extract_query_intent(user_query, primary_table)
        
        # 5. 检查是否需要多表联查
        related_tables = []
        if len(table_matches) > 1 and match_score < 0.8:
            related_tables = self._plan_joins(table_matches[1:], user_query)
        
        # 6. 生成SQL查询
        sql_query = self._generate_sql(primary_table, related_tables, query_intent, user_query)
        
        # 7. 确定展示类型
        chart_type = self._determine_chart_type(query_intent, user_query)
        
        return {
            "success": True,
            "primary_table": primary_table,
            "related_tables": related_tables,
            "sql_query": sql_query,
            "query_intent": query_intent,
            "chart_type": chart_type,
            "table_matches": table_matches
        }
    
    def _extract_query_intent(self, query: str, table_name: str = None) -> Dict[str, Any]:
        """提取查询意图"""
        intent = {}
        query_lower = query.lower()

        # 提取聚合操作
        for pattern_name, pattern in self.query_patterns.items():
            if re.search(pattern, query_lower):
                intent[pattern_name] = True

        # 提取数字和时间范围
        intent['numbers'] = [int(n) for n in re.findall(r'\d+', query)]

        # 提取具体字段
        intent['fields'] = self._extract_fields(query_lower)

        # 提取时间条件（传入表名以使用正确的时间字段）
        intent['time_conditions'] = self._extract_time_conditions(query_lower, table_name)

        # 提取分组字段
        intent['group_field'] = self._extract_group_field(query, table_name)

        return intent
    
    def _extract_fields(self, query: str) -> List[str]:
        """提取查询中提到的字段"""
        common_fields = {
            'id': ['id', '编号', 'ID'],
            'name': ['name', 'name', '名称', '姓名', '标题'],
            'email': ['email', '邮箱', '邮件'],
            'time': ['time', 'time', '时间', '日期'],
            'date': ['date', 'date', '日期'],
            'count': ['count', 'count', '数量', '个数'],
            'status': ['status', 'status', '状态'],
            'type': ['type', 'type', '类型', '种类'],
        }
        
        found_fields = []
        for field, keywords in common_fields.items():
            for keyword in keywords:
                if keyword in query:
                    found_fields.append(field)
                    break
        
        return found_fields

    def _extract_group_field(self, query: str, table_name: str) -> Optional[str]:
        """提取分组统计的字段名"""
        if not table_name:
            return None

        table_info = self.db.get_table_structure(table_name)
        if not table_info or not table_info.get('column_names'):
            return None

        query_lower = query.lower()
        columns = table_info['column_names']

        # 1. 尝试在查询中找到明确的字段名
        for col in columns:
            if col.lower() in query_lower:
                return col

        # 2. 尝试匹配常见的字段名模式
        # module, type, category, status等常见的分组字段
        group_keywords = ['module', 'type', 'category', 'status', 'level', 'group', 'class']
        for col in columns:
            col_lower = col.lower()
            for keyword in group_keywords:
                if keyword in col_lower:
                    return col

        return None
    
    def _extract_time_conditions(self, query: str, table_name: str = None) -> List[Dict[str, Any]]:
        """提取时间条件，返回条件列表（包含字段名和条件）"""
        conditions = []
        time_field = 'created_at'  # 默认时间字段

        # 如果指定了表名，使用对应的时间字段
        if table_name and table_name in self.time_field_mappings:
            time_field = self.time_field_mappings[table_name]

        # 1. 灵活时间范围 - 最近X天
        last_days_match = re.search(self.query_patterns['last_days'], query)
        if last_days_match:
            days = int(last_days_match.group(2))
            conditions.append({
                'field': time_field,
                'condition': f"DATE({time_field}) >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)",
                'description': f'最近{days}天'
            })
            return conditions  # 找到灵活时间范围后直接返回

        # 2. 灵活时间范围 - 最近X周
        last_weeks_match = re.search(self.query_patterns['last_weeks'], query)
        if last_weeks_match:
            weeks = int(last_weeks_match.group(2))
            conditions.append({
                'field': time_field,
                'condition': f"{time_field} >= DATE_SUB(NOW(), INTERVAL {weeks} WEEK)",
                'description': f'最近{weeks}周'
            })
            return conditions

        # 3. 灵活时间范围 - 最近X个月
        last_months_match = re.search(self.query_patterns['last_months'], query)
        if last_months_match:
            months = int(last_months_match.group(2))
            conditions.append({
                'field': time_field,
                'condition': f"{time_field} >= DATE_SUB(NOW(), INTERVAL {months} MONTH)",
                'description': f'最近{months}个月'
            })
            return conditions

        # 4. 固定时间范围 - 今天
        if re.search(self.query_patterns['today'], query):
            conditions.append({
                'field': time_field,
                'condition': f"DATE({time_field}) = CURDATE()",
                'description': '今天'
            })

        # 5. 固定时间范围 - 昨天
        elif re.search(self.query_patterns['yesterday'], query):
            conditions.append({
                'field': time_field,
                'condition': f"DATE({time_field}) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
                'description': '昨天'
            })

        # 6. 固定时间范围 - 本周
        elif re.search(self.query_patterns['this_week'], query):
            conditions.append({
                'field': time_field,
                'condition': f"YEARWEEK({time_field}, 1) = YEARWEEK(CURDATE(), 1)",
                'description': '本周'
            })

        # 7. 固定时间范围 - 上周
        elif re.search(self.query_patterns.get('last_week', r'(上周|上一周)'), query):
            conditions.append({
                'field': time_field,
                'condition': f"YEARWEEK({time_field}, 1) = YEARWEEK(DATE_SUB(CURDATE(), INTERVAL 1 WEEK), 1)",
                'description': '上周'
            })

        # 8. 固定时间范围 - 本月
        elif re.search(self.query_patterns['this_month'], query):
            conditions.append({
                'field': time_field,
                'condition': f"MONTH({time_field}) = MONTH(CURDATE()) AND YEAR({time_field}) = YEAR(CURDATE())",
                'description': '本月'
            })

        # 9. 固定时间范围 - 上月
        elif re.search(self.query_patterns.get('last_month', r'(上个月|上月)'), query):
            conditions.append({
                'field': time_field,
                'condition': f"MONTH({time_field}) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) AND YEAR({time_field}) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))",
                'description': '上月'
            })

        # 10. 固定时间范围 - 今年
        elif re.search(self.query_patterns['this_year'], query):
            conditions.append({
                'field': time_field,
                'condition': f"YEAR({time_field}) = YEAR(CURDATE())",
                'description': '今年'
            })

        return conditions
    
    def _plan_joins(self, table_matches: List[Tuple[str, float]], query: str) -> List[str]:
        """规划表连接"""
        join_tables = []
        
        for table_name, score in table_matches:
            if score > 0.3:  # 只考虑有一定相关性的表
                join_tables.append(table_name)
        
        return join_tables
    
    def _generate_sql(self, primary_table: str, related_tables: List[str], 
                    intent: Dict[str, Any], original_query: str) -> str:
        """生成SQL查询"""
        
        # 基础SELECT部分
        if intent.get('count'):
            select_clause = "SELECT COUNT(*) as count_value"
        elif intent.get('sum') and intent.get('fields'):
            field = intent['fields'][0] if intent['fields'] else '*'
            select_clause = f"SELECT SUM({field}) as sum_value"
        elif intent.get('avg') and intent.get('fields'):
            field = intent['fields'][0] if intent['fields'] else '*'
            select_clause = f"SELECT AVG({field}) as avg_value"
        elif intent.get('max') and intent.get('fields'):
            field = intent['fields'][0] if intent['fields'] else '*'
            select_clause = f"SELECT MAX({field}) as max_value"
        elif intent.get('min') and intent.get('fields'):
            field = intent['fields'][0] if intent['fields'] else '*'
            select_clause = f"SELECT MIN({field}) as min_value"
        else:
            # 默认选择主要字段
            table_info = self.db.get_table_structure(primary_table)
            if table_info and table_info.get('column_names'):
                # 列表/分页查询：选择所有字段，特别是时间字段
                if intent.get('pagination') or '列表' in original_query or '详情' in original_query:
                    # 优先选择时间字段，排除timezone等非时间戳字段
                    cols = table_info['column_names']
                    # 优先包含时间相关的字段（排除timezone等）
                    time_cols = [c for c in cols if any(t in c.lower() for t in ['time', 'date', 'created', 'updated'])
                                and 'timezone' not in c.lower() and 'language' not in c.lower()]
                    other_cols = [c for c in cols if c not in time_cols]
                    # 组合：时间字段优先，然后是其他字段，最多选择10个
                    selected_cols = (time_cols + other_cols)[:10]
                    select_clause = f"SELECT {', '.join(selected_cols)}"
                else:
                    # 普通查询：选择前5个字段
                    cols = table_info['column_names'][:5]
                    select_clause = f"SELECT {', '.join(cols)}"
            else:
                select_clause = "SELECT *"
        
        # FROM和JOIN部分
        from_clause = f"FROM {primary_table}"
        
        # WHERE部分
        where_conditions = intent.get('time_conditions', [])
        # 处理新的时间条件格式（字典列表）
        if where_conditions and isinstance(where_conditions[0], dict):
            where_clauses = [cond['condition'] for cond in where_conditions]
        else:
            # 兼容旧格式（字符串列表）
            where_clauses = where_conditions

        # 添加额外的文本匹配条件
        if '用户' in original_query.lower():
            # 尝试匹配用户相关的字段
            user_fields = ['username', 'name', 'email', 'user_name']
            for field in user_fields:
                table_info = self.db.get_table_structure(primary_table)
                if table_info and field in table_info.get('column_names', []):
                    # 这里可以添加更精确的匹配逻辑
                    break

        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)
        else:
            where_clause = ""
        
        # ORDER BY部分
        order_clause = ""
        if intent.get('order_desc'):
            table_info = self.db.get_table_structure(primary_table)
            if table_info and table_info.get('column_names'):
                # 查找时间字段用于排序
                time_fields = ['created_at', 'time', 'timestamp', 'date']
                for field in time_fields:
                    if field in table_info['column_names']:
                        order_clause = f"ORDER BY {field} DESC"
                        break
                if not order_clause:
                    order_clause = f"ORDER BY {table_info['column_names'][0]} DESC"
        elif intent.get('order_asc'):
            table_info = self.db.get_table_structure(primary_table)
            if table_info and table_info.get('column_names'):
                order_clause = f"ORDER BY {table_info['column_names'][0]} ASC"
        elif intent.get('pagination') or '列表' in original_query or '详情' in original_query:
            # 列表/分页查询：默认按时间倒序（最新的在前）
            table_info = self.db.get_table_structure(primary_table)
            if table_info and table_info.get('column_names'):
                # 优先查找时间字段，排除timezone等非时间戳字段
                # 优先级：created/updated时间 > xxx_time > xxx_date > 包含time的列名
                time_priority_patterns = [
                    'created_at', 'updated_at', 'create_time', 'update_time',  # 高优先级
                    '_time', '_date', 'time_', 'date_',  # 中优先级（后缀/前缀）
                    'timestamp',  # 时间戳
                ]

                time_field = None
                for pattern in time_priority_patterns:
                    for col in table_info['column_names']:
                        if pattern in col.lower() and 'timezone' not in col.lower():
                            time_field = col
                            break
                    if time_field:
                        break

                if time_field:
                    order_clause = f"ORDER BY {time_field} DESC"
                else:
                    order_clause = f"ORDER BY {table_info['column_names'][0]} DESC"
        
        # LIMIT部分
        limit_clause = ""
        if intent.get('pagination'):
            # 分页查询时设置合理的上限，避免查询过多数据
            numbers = intent.get('numbers', [])
            if numbers:
                # 用户指定了每页数量
                page_size = numbers[0]
            else:
                # 默认最多查询10000条，前端JS进行客户端分页
                page_size = 10000
            limit_clause = f"LIMIT {page_size}"
        elif not intent.get('count') and not intent.get('group_field'):  # 非统计、非分组查询默认限制
            limit_clause = "LIMIT 100"

        # GROUP BY部分
        group_clause = ""
        group_field = intent.get('group_field')
        if group_field and intent.get('group_by'):
            # 修改SELECT子句以支持分组统计
            select_clause = f"SELECT {group_field}, COUNT(*) as count_value"
            group_clause = f"GROUP BY {group_field}"
            # 分组统计默认按计数降序排列
            if not order_clause:
                order_clause = f"ORDER BY count_value DESC"

        # 组合SQL
        sql_parts = [select_clause, from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if group_clause:
            sql_parts.append(group_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if limit_clause:
            sql_parts.append(limit_clause)

        return " ".join(sql_parts)
    
    def _determine_chart_type(self, intent: Dict[str, Any], query: str) -> str:
        """确定图表类型"""
        # 分组统计查询使用表格或柱状图
        if intent.get('group_field') and intent.get('group_by'):
            return "table"  # 分组统计结果用表格显示更清晰

        # 统计类查询使用单值显示
        if intent.get('count') or intent.get('sum') or intent.get('avg'):
            return "single_value"

        # 时间趋势相关使用折线图
        if intent.get('time_conditions') and '趋势' in query:
            return "line_chart"

        # 对比类查询使用柱状图
        if '对比' in query or '比较' in query:
            return "bar_chart"

        # 分页查询使用表格
        if intent.get('pagination') or '列表' in query or '详情' in query:
            return "table"

        # 默认使用表格
        return "table"