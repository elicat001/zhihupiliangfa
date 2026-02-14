"""
模型包初始化
在此处导入所有模型，确保 SQLAlchemy Base.metadata 能注册全部表。
init_db() 只需 import app.models 即可触发所有模型注册。
"""

from app.models.account import Account  # noqa: F401
from app.models.article import Article  # noqa: F401
from app.models.task import PublishTask, PublishRecord  # noqa: F401
from app.models.log import SystemLog  # noqa: F401
from app.models.template import PromptTemplate  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.pilot import ContentDirection, GeneratedTopic  # noqa: F401
