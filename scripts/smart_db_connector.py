#!/usr/bin/env python3
"""
智能数据库连接和表发现系统
支持自动发现表结构、智能匹配用户查询、生成SQL并执行
"""

try:
    import mysql.connector
except ImportError:
    print("❌ 需要安装mysql-connector-python: pip install mysql-connector-python")
    exit(1)

import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

class SmartDBConnector:
    def __init__(self, config_file: str = "db_config.json"):
        """初始化智能数据库连接器"""
        self.config_file = config_file
        self.connection = None
        self.config = self._load_config()
        self.table_cache = {}
        self.table_keywords = {}
    
    def _load_config(self) -> Dict[str, Any]:
        """加载数据库配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            default_config = {
                "host": "localhost",
                "port": 3306,
                "user": "your_username",
                "password": "your_password",
                "database": "your_database",
                "charset": "utf8mb4"
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"📝 已创建数据库配置文件: {self.config_file}")
            print("请编辑配置文件中的数据库连接信息后重新运行")
            return default_config
    
    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                print(f"✅ 成功连接到MySQL数据库: {self.config['database']}")
                return True
        except mysql.connector.Error as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
        return False
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 数据库连接已关闭")
    
    def discover_tables(self) -> Dict[str, Dict[str, Any]]:
        """发现数据库中的所有表及其结构"""
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return {}
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # 获取所有表名
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [list(row.values())[0] for row in tables]
            
            table_info = {}
            
            for table_name in table_names:
                # 获取表结构
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                
                # 处理列信息
                column_names = []
                primary_keys = []
                
                for col in columns:
                    try:
                        field_name = col['Field']
                        key_type = col['Key']
                        column_names.append(field_name)
                        if key_type == 'PRI':
                            primary_keys.append(field_name)
                    except (KeyError, TypeError):
                        # 如果字典访问失败，使用索引方式
                        field_name = col[0]
                        key_type = col[3] if len(col) > 3 else ''
                        column_names.append(field_name)
                        if key_type == 'PRI':
                            primary_keys.append(field_name)
                
                table_info[table_name] = {
                    'columns': columns,
                    'column_names': column_names,
                    'primary_keys': primary_keys,
                    'foreign_keys': [],  # 可以进一步扩展获取外键信息
                }
            
            # 缓存表信息
            self.table_cache = table_info
            
            # 生成表关键词
            self._generate_table_keywords()
            
            cursor.close()
            print(f"📋 发现 {len(table_names)} 个表: {', '.join(table_names)}")
            return table_info
            
        except mysql.connector.Error as e:
            print(f"❌ 发现表失败: {e}")
            if cursor:
                cursor.close()
            return {}
    
    def _generate_table_keywords(self):
        """为每个表生成关键词映射（完全基于表结构，不依赖硬编码）"""
        table_keyword_map = {}

        for table_name, info in self.table_cache.items():
            keywords = set()

            # 表名本身（各种形式）
            keywords.add(table_name.lower())

            # 拆分表名中的关键词（支持多种分隔符）
            parts = re.split(r'[_\s-]+', table_name.lower())
            for part in parts:
                if len(part) > 2:
                    keywords.add(part)
                    # 添加常见的缩写形式
                    if len(part) > 4:
                        # 添加前4个字符作为关键词
                        keywords.add(part[:4])

            # 列名作为关键词
            for col in info['column_names']:
                col_parts = re.split(r'[_\s-]+', col.lower())
                for part in col_parts:
                    if len(part) > 2:
                        keywords.add(part)

            table_keyword_map[table_name] = list(keywords)

        self.table_keywords = table_keyword_map
    
    def match_tables(self, user_query: str) -> List[Tuple[str, float]]:
        """根据用户查询匹配相关的表"""
        user_query_lower = user_query.lower()
        # 支持中文分词：每个中文字符单独分词，英文单词保持完整
        user_words = set()
        # 匹配连续的中文字符（每个单独作为一个词）
        for char in user_query_lower:
            if '\u4e00' <= char <= '\u9fff':
                user_words.add(char)
        # 匹配英文单词、数字、下划线
        user_words.update(re.findall(r'[a-zA-Z0-9_]+', user_query_lower))
        
        table_scores = []
        
        for table_name, keywords in self.table_keywords.items():
            score = 0
            keyword_set = set(keywords)
            
            # 计算关键词匹配度
            intersection = user_words.intersection(keyword_set)
            if intersection:
                score += len(intersection) / len(keyword_set) * 0.6
            
            # 使用模糊匹配
            for word in user_words:
                for keyword in keyword_set:
                    similarity = SequenceMatcher(None, word, keyword).ratio()
                    if similarity > 0.7:
                        score += similarity * 0.4
            
            if score > 0:
                table_scores.append((table_name, score))
        
        # 按分数排序
        table_scores.sort(key=lambda x: x[1], reverse=True)
        return table_scores
    
    def get_table_structure(self, table_name: str) -> Dict[str, Any]:
        """获取指定表的结构信息"""
        if table_name in self.table_cache:
            return self.table_cache[table_name]
        
        # 如果缓存中没有，实时获取
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return {}
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            cursor.close()
            
            # 处理列信息
            column_names = []
            primary_keys = []
            
            for col in columns:
                try:
                    field_name = col['Field']
                    key_type = col['Key']
                    column_names.append(field_name)
                    if key_type == 'PRI':
                        primary_keys.append(field_name)
                except (KeyError, TypeError):
                    field_name = col[0]
                    key_type = col[3] if len(col) > 3 else ''
                    column_names.append(field_name)
                    if key_type == 'PRI':
                        primary_keys.append(field_name)
            
            info = {
                'columns': columns,
                'column_names': column_names,
                'primary_keys': primary_keys,
            }
            
            self.table_cache[table_name] = info
            return info
            
        except mysql.connector.Error as e:
            print(f"❌ 获取表结构失败: {e}")
            if cursor:
                cursor.close()
            return {}
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """执行SQL查询"""
        if not self.connection or not self.connection.is_connected():
            if not self.connect():
                return {"success": False, "error": "无法连接到数据库"}
        
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            # 判断是否为查询语句
            if cursor.description:
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                return {
                    "success": True,
                    "data": results,
                    "columns": columns,
                    "row_count": len(results),
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # 对于INSERT, UPDATE, DELETE语句
                self.connection.commit()
                return {
                    "success": True,
                    "affected_rows": cursor.rowcount,
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
                
        except mysql.connector.Error as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            if cursor:
                cursor.close()

    def suggest_related_tables(self, primary_table: str, user_query: str) -> List[Tuple[str, float]]:
        """建议可能与主表相关的表"""
        if not self.table_cache:
            self.discover_tables()
        
        primary_info = self.get_table_structure(primary_table)
        if not primary_info:
            return []
        
        primary_columns = set(primary_info['column_names'])
        suggestions = []
        
        for table_name, info in self.table_cache.items():
            if table_name == primary_table:
                continue
            
            # 查找共同的列名（可能是外键关系）
            common_columns = primary_columns.intersection(info['column_names'])
            if common_columns:
                score = len(common_columns) / max(len(primary_columns), len(info['column_names']))
                suggestions.append((table_name, score))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        if self.connect():
            self.disconnect()
            return True
        return False