import math
from collections import Counter
from models import Topic, BlogPost, load_database

# 从本地加载的数据库会话
session_db = load_database()


# 使用余弦相似度算法计算两个关键词列表的相似度
def topic_cosine_similarity(list1, list2):
    if not list1 or not list2:
        return 0.0
    vec1 = Counter(list1)
    vec2 = Counter(list2)
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


# 判断两个关键词列表的相似度是否高于指定的阈值
def is_similar_keywords(keywords1, keywords2, threshold=0.5):
    similarity = topic_cosine_similarity(keywords1, keywords2)
    return similarity > threshold


# 合并相似度高的话题
def merge_topics(session, batch_size=500):
    session = session()
    offset = 0
    while True:
        # 获取一批话题
        topics_batch = session.query(Topic).offset(offset).limit(batch_size).all()
        if not topics_batch:
            break

        topics_dict = {topic.uuid: topic for topic in topics_batch}
        merged = set()

        for uuid1, topic1 in topics_dict.items():
            if uuid1 in merged:
                continue
            for uuid2, topic2 in topics_dict.items():
                if uuid1 != uuid2 and is_similar_keywords(topic1.keywords, topic2.keywords):
                    print(f"合并以下两个话题: {topic1.topic_title, topic2.topic_title}")
                    if topic1.post_count >= topic2.post_count:
                        topic1.blogposts.extend(topic2.blogposts)
                        topic1.blogposts = list(set(topic1.blogposts))  # 去重
                        topic1.post_count = len(topic1.blogposts)
                        update_blogposts(session, topic2.uuid, topic1.uuid)
                        session.delete(topic2)
                    else:
                        topic2.blogposts.extend(topic1.blogposts)
                        topic2.blogposts = list(set(topic2.blogposts))  # 去重
                        topic2.post_count = len(topic2.blogposts)
                        update_blogposts(session, topic1.uuid, topic2.uuid)
                        session.delete(topic1)
                    session.commit()
                    merged.add(uuid2)

        offset += batch_size


# 更新被合并话题相关的博文
def update_blogposts(session, old_uuid, new_uuid):
    blogposts = session.query(BlogPost).all()
    for post in blogposts:
        if any(topic['uuid'] == old_uuid for topic in post.topics):
            post.topics = [
                {'uuid': new_uuid if topic['uuid'] == old_uuid else topic['uuid']}
                for topic in post.topics]
            session.commit()
