import numpy as np
from sklearn.decomposition import PCA
from data_analysis import calculate_average_likes_count, calculate_average_comments_count, \
    calculate_average_reposts_count
from models import Topic, Weight


# 将所有话题的post_counts和avg_*属性汇总成列表，留待determine_weights_pca函数进行分析
def analyze_all_topics(session_db):
    topics = session_db.query(Topic).all()
    all_post_counts = []
    all_avg_likes = []
    all_avg_comments = []
    all_avg_reposts = []

    for topic in topics:
        all_post_counts.append(topic.post_count)
        all_avg_likes.append(topic.avg_likes)
        all_avg_comments.append(topic.avg_comments)
        all_avg_reposts.append(topic.avg_reposts)

    return all_post_counts, all_avg_likes, all_avg_comments, all_avg_reposts


# 使用主成分分析法获取权重
def determine_weights_pca(all_post_counts, all_avg_likes, all_avg_comments, all_avg_reposts):
    # 准备数据
    X = np.column_stack([all_post_counts, all_avg_likes, all_avg_comments, all_avg_reposts])

    # 主成分分析
    pca = PCA(n_components=1)
    pca.fit(X)

    # 获取每个属性的权重
    weights = pca.components_[0]
    return weights / weights.sum()


# 获取权重
def get_weight(session_db):
    weight = session_db.query(Weight).first()

    if weight is None:
        # 权重值尚未计算过，执行权重计算
        all_post_counts, all_avg_likes, all_avg_comments, all_avg_reposts = analyze_all_topics(session_db)
        post_count_weight, avg_likes_weight, avg_comments_weight, avg_reposts_weight = determine_weights_pca(
            all_post_counts,
            all_avg_likes,
            all_avg_comments,
            all_avg_reposts
        )

        # 将计算出来的权重值存储到数据库中
        weight = Weight(
            post_count_weight=post_count_weight,
            avg_likes_weight=avg_likes_weight,
            avg_comments_weight=avg_comments_weight,
            avg_reposts_weight=avg_reposts_weight
        )
        session_db.add(weight)
        session_db.commit()
    else:
        # 从数据库中读取权重值
        post_count_weight = weight.post_count_weight
        avg_likes_weight = weight.avg_likes_weight
        avg_comments_weight = weight.avg_comments_weight
        avg_reposts_weight = weight.avg_reposts_weight

    session_db.close()
    return post_count_weight, avg_likes_weight, avg_comments_weight, avg_reposts_weight

# 计算某个话题的热度值
def calculate_hot_rate(post_count, avg_likes, avg_comments, avg_reposts, post_count_weight, avg_likes_weight,
                       avg_comments_weight, avg_reposts_weight):
    hot_rate = (post_count * post_count_weight +
                avg_likes * avg_likes_weight +
                avg_comments * avg_comments_weight +
                avg_reposts * avg_reposts_weight)
    return int(hot_rate)

# 更新全体话题的热度值到数据库
def update_topics_hot_rate(session_db):
    post_count_weight, avg_likes_weight, avg_comments_weight, avg_reposts_weight = get_weight(session_db)
    topics = session_db.query(Topic).all()
    for topic in topics:
        avg_likes = calculate_average_likes_count(session_db, topic.uuid)
        avg_comments = calculate_average_comments_count(session_db, topic.uuid)
        avg_reposts = calculate_average_reposts_count(session_db, topic.uuid)
        hot_rate = calculate_hot_rate(topic.post_count, avg_likes, avg_comments, avg_reposts, post_count_weight,
                                      avg_likes_weight, avg_comments_weight, avg_reposts_weight)
        topic.hot_rate = hot_rate
        session_db.commit()
