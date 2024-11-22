from datetime import datetime, timedelta
from data_analysis import calculate_average_comments_count, calculate_average_reposts_count, \
    calculate_average_likes_count, get_blogposts_for_topic
from topic_emotion import update_topics_emotions
from topic_hot_rate import update_topics_hot_rate
from models import BlogPost, Topic, load_database
from topic_recognition import match_topics_to_blogposts
from topic_stage import update_topics_hot_rate_per_hr, update_topics_stage


# 显示数据库中的blogpost，调试信息
def display_posts(session):
    blogposts = session.query(BlogPost).all()
    blogposts_cnt = session.query(BlogPost).count()
    print("Blog Posts:")
    for post in blogposts:
        print(f"ID: {post.id}, Username: {post.username}, Text: {post.text}, Date: {post.date}, "
              f"Reposts: {post.reposts_count}, Comments: {post.comments_count}, Likes: {post.likes_count}, "
              f"Topics: {post.topics}, Keywords: {post.keywords}, Emotions: {post.emotion}")
    print(f"Blogposts: {blogposts_cnt}")


# 显示数据库中的topic，调试信息
def display_topics(session):
    topics = session.query(Topic).all()
    topics_cnt = session.query(Topic).count()
    print("\nTopics:")
    for topic in topics:
        print(f"Title: {topic.topic_title}, UUID: {topic.uuid}, Stage: {topic.stage}, Posts: {topic.post_count}, "
              f"Keywords: {topic.keywords}, BlogPosts: {topic.blogposts}")
        print(f"post_keywords: {topic.post_keywords}, Hot_rate: {topic.hot_rate}, "
              f"Emotions: {topic.emotion}, Avg_Likes: {topic.avg_likes}, Avg_comments: {topic.avg_comments}, "
              f"Avg_reposts: {topic.avg_reposts}, Hot rate per hour: {topic.hot_rate_per_hr}")

    print(f"topics: {topics_cnt}")


# 打印数据库中的所有数据
def display_data():
    session = load_database()
    display_posts(session)
    display_topics(session)


# 删除超过 72 小时的 BlogPost 并更新或删除相应的 Topic
def clean_old_blogposts(session):
    session = session()
    three_days_ago = datetime.now() - timedelta(hours=72)

    old_posts = session.query(BlogPost).filter(BlogPost.date < three_days_ago).all()
    for post in old_posts:
        topics = post.topics
        for topic in topics:
            topic_uuid = topic['uuid']
            existing_topic = session.query(Topic).filter_by(uuid=topic_uuid).first()
            if existing_topic:
                # 减少 post_count 并从 blogposts 列表中删除该 post 的 id
                existing_topic.post_count -= 1
                existing_topic.blogposts = [bp_id for bp_id in existing_topic.blogposts if bp_id != post.id]

                # 如果 post_count 为 0，则删除该 Topic
                if existing_topic.post_count == 0:
                    session.delete(existing_topic)
                session.commit()

        # 删除 BlogPost
        session.delete(post)
        session.commit()

    session.close()
    print("成功清理过期数据")


# 对所有topic的post_count进行更新
def update_topics_post_count(session_db):
    topics = session_db.query(Topic).all()
    for topic in topics:
        topic.post_count = len(topic.blogposts)
    session_db.commit()


# 获取某个话题的post_keywords（该话题相关的blog的keywords的集合字典，包含keyword名和频数），用于话题页的话题词云图生成
def update_topic_post_keywords(session_db, topic_uuid):
    topic = session_db.query(Topic).filter_by(uuid=topic_uuid).first()
    if not topic:
        return

    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    keyword_freq = {}
    for bp in blogposts:
        for keyword in bp.keywords:
            if keyword in keyword_freq:
                keyword_freq[keyword] += 1
            else:
                keyword_freq[keyword] = 1

    topic.post_keywords = keyword_freq
    session_db.commit()
    return keyword_freq


# 更新所有话题的post_keywords
def update_topics_post_keywords(session_db):
    topics = session_db.query(Topic).all()
    for topic in topics:
        update_topic_post_keywords(session_db, topic.uuid)
    session_db.commit()


# 对所有topic的avg_*字段进行更新
def update_topics_avgs(session_db):
    topics = session_db.query(Topic).all()
    for topic in topics:
        topic.avg_likes = calculate_average_likes_count(session_db, topic.uuid)
        topic.avg_reposts = calculate_average_reposts_count(session_db, topic.uuid)
        topic.avg_comments = calculate_average_comments_count(session_db, topic.uuid)
    session_db.commit()


# 对topic的主要属性进行更新
def update_topics_attributes(session_db):
    print("写入Topic.avgs...")
    update_topics_avgs(session_db)
    print("写入Topic.emotions...")
    update_topics_emotions(session_db)


# 将所有topics内的属性进行更新
def update_topics_all(session):
    session = session()

    print("识别博文主题中...")
    match_topics_to_blogposts(session)
    print("写入Topic.post_count...")
    update_topics_post_count(session)
    update_topics_attributes(session)
    print("写入Topic.post_keywords...")
    update_topics_post_keywords(session)
    print("写入Topic.hot_rate...")
    update_topics_hot_rate(session)
    print("写入Topic.hot_rate_per_hr...")
    update_topics_hot_rate_per_hr(session)
    print("写入Topic.stage...")
    update_topics_stage(session)
