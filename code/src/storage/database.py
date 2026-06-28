"""SQLite 数据库连接与表管理。

提供基础接口：
- get_connection()：获取数据库连接
- init_db()：创建所有表
- execute_query() / execute_write()：参数化查询封装
"""

import os
import sqlite3
import threading
from typing import Any, Optional

from loguru import logger

from src.utils.config import DB_PATH, DATA_DIR

# 写锁：保护所有 INSERT / UPDATE / DELETE 操作
_write_lock = threading.Lock()

# 线程本地存储：每个线程持有自己的连接
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """获取当前线程的数据库连接（自动创建）。"""
    conn = getattr(_local, "connection", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.connection = conn
    return conn


def close_connection() -> None:
    """关闭当前线程的数据库连接。"""
    conn = getattr(_local, "connection", None)
    if conn is not None:
        conn.close()
        _local.connection = None


def init_db() -> None:
    """创建所有数据库表（IF NOT EXISTS 保证幂等）。"""
    conn = get_connection()
    with _write_lock:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                avatar TEXT,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                sender_type TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_edited INTEGER DEFAULT 0,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_contact_time
                ON messages(contact_id, timestamp DESC);

            CREATE TABLE IF NOT EXISTS profiles (
                contact_id INTEGER PRIMARY KEY,
                basic_info TEXT,
                personality TEXT,
                hobbies TEXT,
                behavior_patterns TEXT,
                affinity_score INTEGER DEFAULT 0,
                summary TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skill_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                contact_id INTEGER,
                input_summary TEXT,
                output_summary TEXT,
                token_used INTEGER,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL
            );
        """)
        # 迁移：为旧数据库添加 notes 列
        try:
            conn.execute("ALTER TABLE contacts ADD COLUMN notes TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 列已存在

        conn.commit()
    logger.info(f"数据库初始化完成: {DB_PATH}")


def execute_query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """执行只读查询，返回 Row 列表。"""
    conn = get_connection()
    cursor = conn.execute(sql, params)
    return cursor.fetchall()


def execute_write(sql: str, params: tuple = ()) -> int:
    """执行写操作（INSERT/UPDATE/DELETE），返回 lastrowid。"""
    conn = get_connection()
    with _write_lock:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid


def execute_insert(sql: str, params: tuple = ()) -> int:
    """执行 INSERT，返回新行的 id。"""
    return execute_write(sql, params)
