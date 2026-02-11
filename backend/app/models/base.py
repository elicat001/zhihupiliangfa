"""
SQLAlchemy ORM 基类
所有模型都继承自此 Base
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """声明式基类"""
    pass
