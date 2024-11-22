# 使用jieba提取话题关键词（最多不超过5个），保存到数据库
import jieba
import jieba.analyse
from models import Topic, BlogPost


# 提取话题的关键词并保存到数据库
def extract_topic_keywords(session):
    topics = session.query(Topic).all()
    for topic in topics:
        if len(topic.keywords) == 0:
            keywords = jieba.analyse.extract_tags(topic.topic_title, topK=5)
            topic.keywords = keywords
    session.commit()


# 提取博文的关键词并保存到数据库
def extract_post_keywords(session):
    posts = session.query(BlogPost).all()
    for post in posts:
        if len(post.keywords) == 0:
            keywords = jieba.analyse.extract_tags(post.text, topK=10)
            post.keywords = keywords
    session.commit()


# 提取关键词的总函数
def extract_keywords(session):
    extract_post_keywords(session)
    extract_topic_keywords(session)
