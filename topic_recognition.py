import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import or_
from machine_learning import prediction, training
from models import Topic, BlogPost, load_database

session_db = load_database()


# 准备训练数据
def prepare_data_for_training(blogposts, topics):
    X = []
    y = []
    topic_dict = {topic.uuid: " ".join(topic.keywords) for topic in topics}
    for bp in blogposts:
        if bp.topics:
            keywords_str = " ".join(bp.keywords)
            for topic in bp.topics:
                if str(topic['uuid']) in topic_dict:
                    X.append(keywords_str)
                    y.append(topic_dict[str(topic['uuid'])])
    return X, y


# 匹配话题到博文（AI版本，弃用）
def match_topics_to_blogposts_ai_ver(threshold=0.5):
    # 获取所有没有话题的BlogPost
    blogposts_without_topic = session_db.query(BlogPost).filter(BlogPost.topics == []).all()
    topics = session_db.query(Topic).all()

    if not blogposts_without_topic or not topics:
        print("没有需要匹配的话题或博文。")
        return

    # 获取所有有话题的BlogPost用于训练
    blogposts_with_topics = session_db.query(BlogPost).filter(
        BlogPost.topics != []
    ).all()

    X_new = []
    for bp in blogposts_without_topic:
        keywords_str = " ".join(bp.keywords)
        X_new.append(keywords_str)
    # 准备训练数据
    X_train, y_train = prepare_data_for_training(blogposts_with_topics, topics)
    training(X_train, y_train)
    y_new = prediction(X_new, y_train)
    print(f"训练集长度: X: {len(X_train)}, Y: {len(y_train)}")


# 匹配话题到博文
def match_topics_to_blogposts(session, threshold=0.5):
    # 获取所有没有话题的BlogPost
    blogposts = session.query(BlogPost).filter(
        or_(BlogPost.topics.is_(None), BlogPost.topics == [])
    ).all()

    # 获取所有已知的Topic
    topics = session.query(Topic).all()

    if not blogposts or not topics:
        print("没有需要匹配的话题或博文。")
        return

    # 向量化所有话题关键词
    topic_keywords = [" ".join(topic.keywords) for topic in topics]
    vectorizer = TfidfVectorizer()
    topic_vectors = vectorizer.fit_transform(topic_keywords)

    # 对没有话题的BlogPost进行预测
    for bp in blogposts:
        if not bp.keywords:
            continue

        keywords_str = " ".join(bp.keywords)

        # 向量化博文关键词
        blogpost_vector = vectorizer.transform([keywords_str])

        # 计算余弦相似度
        similarities = cosine_similarity(blogpost_vector, topic_vectors).flatten()

        # 选择与博文关键词最相关的关键词，限制关键词数量不超过5个
        related_topic_indices = np.argsort(similarities)[-5:][::-1]
        related_topics = [(topics[i], similarities[i]) for i in related_topic_indices if similarities[i] > threshold]

        for topic, similarity in related_topics:
            if any(kw in keywords_str for kw in topic.keywords):
                if bp.topics is None:
                    bp.topics = []
                if topic.uuid not in [t['uuid'] for t in bp.topics]:
                    bp.topics.append({"uuid": topic.uuid})
                    print(topic.blogposts)
                    topic.blogposts.append(bp.id)
                    print("合并后: ", topic.blogposts)
                    print(f"将博文{bp.id}: 关键词{bp.keywords}合并到话题{topic.uuid}: 关键词{topic.keywords}")
                    topic.post_count += 1
                    session.add(bp)
                    session.add(topic)

    session.commit()
    session.close()
