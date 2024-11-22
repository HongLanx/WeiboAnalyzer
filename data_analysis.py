from models import BlogPost, Topic
from sqlalchemy import func, String


# 获取某个topic的所有相关blogposts
def get_blogposts_for_topic(session_db, topic_uuid):
    topic = session_db.query(Topic).filter_by(uuid=topic_uuid).first()
    if not topic:
        return []
    blogpost_ids = topic.blogposts
    if not blogpost_ids:
        return []

    # 将 blogpost_ids 转换为字符串进行查询
    blogpost_ids_str = [str(id) for id in blogpost_ids]
    blogposts = session_db.query(BlogPost).filter(func.cast(BlogPost.id, String).in_(blogpost_ids_str)).all()
    return blogposts


# 计算某个topic的平均点赞数
def calculate_average_likes_count(session_db, topic_uuid):
    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    if not blogposts:
        return 0
    total_likes = sum(bp.likes_count for bp in blogposts)
    return total_likes / len(blogposts)


# 计算某个topic的平均转发数
def calculate_average_reposts_count(session_db, topic_uuid):
    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    if not blogposts:
        return 0
    total_reposts = sum(bp.reposts_count for bp in blogposts)
    return total_reposts / len(blogposts)


# 计算某个topic的平均评论数
def calculate_average_comments_count(session_db, topic_uuid):
    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    if not blogposts:
        return 0
    total_comments = sum(bp.comments_count for bp in blogposts)
    return total_comments / len(blogposts)


# 获取数据库中所有BlogPost的总关键词和其词频，用于首页总词云图
def get_all_post_keywords(session_db):
    blogposts = session_db.query(BlogPost).all()
    keyword_freq = {}
    for bp in blogposts:
        for keyword in bp.keywords:
            if keyword in keyword_freq:
                keyword_freq[keyword] += 1
            else:
                keyword_freq[keyword] = 1
    return keyword_freq
