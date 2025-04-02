import pymysql
from typing import Dict, List, Optional, Union

class MySQLDatabase:
    """
    MySQL数据库管理类
    功能：
    - 自动初始化表格
    - 支持事务操作
    - 参数化查询防止SQL注入
    - 基本的CRUD操作
    """
    
    def __init__(self, 
                 host: str,
                 user: str,
                 password: str,
                 database: str,
                 port: int = 3306,
                 charset: str = 'utf8mb4',
                 table_schemas: Optional[Dict[str, str]] = None):
        """
        初始化数据库连接
        
        :param table_schemas: 表结构字典 {表名: CREATE TABLE SQL}
        """
        self.connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset=charsis工，
            cursorclass=pymysql.cursors.DictCursor
        )
        self.cursor = self.connection.cursor()
        self.table_schemas = table_schemas or {}

        # 初始化表格
        for table_name, create_sql in self.table_schemas.items():
            if not self.table_exists(table_name):
                self.execute(create_sql)
                self.commit()

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        self.execute("SHOW TABLES LIKE %s", (table_name,))
        return self.cursor.rowcount > 0

    def execute(self, 
               sql: str, 
               params: Optional[Union[tuple, Dict]] = None, 
               commit: bool = False) -> int:
        """
        执行SQL语句
        
        :return: 受影响的行数
        """
        self.cursor.execute(sql, params)
        if commit:
            self.connection.commit()
        return self.cursor.rowcount

    def commit(self):
        """提交事务"""
        self.connection.commit()

    def rollback(self):
        """回滚事务"""
        self.connection.rollback()

    def insert(self, 
              table: str, 
              data: Dict, 
              commit: bool = True) -> int:
        """
        插入数据
        
        :param table: 表名
        :param data: 数据字典 {列名: 值}
        :return: 插入的行数
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute(sql, tuple(data.values()), commit)

    def select(self, 
              table: str, 
              columns: Union[str, List[str]] = '*', 
              where: Optional[Dict] = None,
              order_by: Optional[str] = None,
              limit: Optional[int] = None) -> List[Dict]:
        """
        查询数据
        
        :param columns: 要查询的列（字符串或列表）
        :param where: 条件字典 {列名: 值}
        :return: 查询结果列表
        """
        if isinstance(columns, list):
            columns = ', '.join(columns)
            
        sql = f"SELECT {columns} FROM {table}"
        params = []
        
        if where:
            conditions = ' AND '.join([f"{k}=%s" for k in where.keys()])
            sql += f" WHERE {conditions}"
            params.extend(where.values())
            
        if order_by:
            sql += f" ORDER BY {order_by}"
            
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)
            
        self.execute(sql, params)
        return self.cursor.fetchall()

    def update(self, 
              table: str, 
              data: Dict, 
              where: Dict, 
              commit: bool = True) -> int:
        """
        更新数据
        
        :return: 受影响的行数
        """
        set_clause = ', '.join([f"{k}=%s" for k in data.keys()])
        conditions = ' AND '.join([f"{k}=%s" for k in where.keys()])
        
        sql = f"UPDATE {table} SET {set_clause} WHERE {conditions}"
        params = list(data.values()) + list(where.values())
        
        return self.execute(sql, params, commit)

    def delete(self, 
              table: str, 
              where: Dict, 
              commit: bool = True) -> int:
        """
        删除数据
        
        :return: 受影响的行数
        """
        conditions = ' AND '.join([f"{k}=%s" for k in where.keys()])
        sql = f"DELETE FROM {table} WHERE {conditions}"
        return self.execute(sql, tuple(where.values()), commit)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.connection.close()

    def close(self):
        """关闭数据库连接"""
        self.connection.close()