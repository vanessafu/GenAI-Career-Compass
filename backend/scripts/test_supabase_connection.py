import os
import contextlib
from typing import Generator
from dotenv import load_dotenv
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from pgvector.psycopg2 import register_vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
try:
    db_pool = SimpleConnectionPool(
        minconn=2,       # Transaction 模式下，本地不需要维持太多长连接
        maxconn=15,      # 限制本地最大并发套接字数
        dsn=DATABASE_URL,
        keepalives=1
    )
    print("Successfully connected to Supabase Pooler (Transaction Mode).")
except Exception as e:
    print(f"Failed to create pool: {e}")