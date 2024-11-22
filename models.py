import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 设置数据库文件路径
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "weibo.db")  # 主数据库路径
DATABASE_COPY_PATH = os.path.join(os.path.dirname(__file__), "weibo_copy.db")  # 备份数据库路径
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)  # 确保数据库目录存在
Base = declarative_base()  # 创建基本映射类


# 定义博文对象
class BlogPost(Base):
    __tablename__ = 'blogposts'  # 数据库表名
    id = Column(Integer, primary_key=True)  # 博文ID
    username = Column(String)  # 博文发布者用户名
    text = Column(Text)  # 博文内容
    date = Column(DateTime)  # 博文发布时间
    reposts_count = Column(Integer)  # 转发数
    comments_count = Column(Integer)  # 评论数
    likes_count = Column(Integer)  # 点赞数
    topics = Column(JSON)  # 相关话题UUID列表
    keywords = Column(JSON, default=[])  # 关键词列表
    emotion = Column(JSON, default=[])  # 情感分析结果


# 定义频道对象
class Channel(Base):
    __tablename__ = 'channels'  # 数据库表名
    title = Column(String)  # 频道标题
    gid = Column(String, primary_key=True)  # 频道ID
    containerid = Column(String)  # 容器ID


# 定义权重对象
class Weight(Base):
    __tablename__ = 'weights'  # 数据库表名
    id = Column(Integer, primary_key=True)  # 权重ID
    post_count_weight = Column(Float, default=0)  # 博文数权重
    avg_likes_weight = Column(Float, default=0)  # 平均点赞权重
    avg_comments_weight = Column(Float, default=0)  # 平均评论权重
    avg_reposts_weight = Column(Float, default=0)  # 平均转发权重


# 定义话题对象
class Topic(Base):
    __tablename__ = 'topics'  # 数据库表名
    topic_title = Column(String)  # 话题标题
    uuid = Column(String, primary_key=True)  # 话题UUID
    stage = Column(Integer, default=0)  # 生命周期阶段
    post_count = Column(Integer, default=0)  # 相关博文数
    keywords = Column(JSON, default=[])  # 关键词列表
    post_keywords = Column(JSON, default=[])  # 博文关键词及词频
    hot_rate = Column(Float, default=0)  # 热度
    blogposts = Column(JSON, default=[])  # 相关博文ID列表
    emotion = Column(JSON, default=[])  # 情感
    avg_likes = Column(Float, default=0)  # 平均点赞数
    avg_comments = Column(Float, default=0)  # 平均评论数
    avg_reposts = Column(Float, default=0)  # 平均转发数
    hot_rate_per_hr = Column(JSON, default={})  # 每小时热度


# 初始化数据库会话
def get_Session(path):
    engine = create_engine(f'sqlite:///{path}')  # 创建数据库引擎
    Base.metadata.create_all(engine)  # 创建所有表
    session = sessionmaker(bind=engine)  # 创建会话类
    return session


Session = get_Session(DATABASE_PATH)  # 主数据库会话
SessionCopy = get_Session(DATABASE_COPY_PATH)  # 备份数据库会话


# 加载数据库
def load_database():
    db_session = Session()  # 创建数据库会话
    return db_session
