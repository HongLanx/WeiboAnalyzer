from datetime import datetime, timedelta
from data_analysis import get_blogposts_for_topic
from topic_hot_rate import calculate_hot_rate, get_weight
from models import Topic


# 更新某一topic的post_freq_per_hr属性
def update_topic_hot_rate_per_hr(session_db, topic_uuid):
    topic = session_db.query(Topic).filter_by(uuid=topic_uuid).first()
    if not topic:
        return

    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    if not blogposts:
        return

    post_count_weight, avg_likes_weight, avg_comments_weight, avg_reposts_weight = get_weight(session_db)

    hot_rate_per_hr = {}
    for i in range(24):
        start_time = datetime.now() - timedelta(hours=(i + 1) * 3)
        end_time = datetime.now() - timedelta(hours=i * 3)
        relevant_posts = [bp for bp in blogposts if start_time <= bp.date < end_time]
        if relevant_posts:
            avg_hot_rate = calculate_hot_rate(
                len(relevant_posts),
                sum(bp.likes_count for bp in relevant_posts) / len(relevant_posts),
                sum(bp.comments_count for bp in relevant_posts) / len(relevant_posts),
                sum(bp.reposts_count for bp in relevant_posts) / len(relevant_posts),
                post_count_weight,
                avg_likes_weight,
                avg_comments_weight,
                avg_reposts_weight
            )
        else:
            avg_hot_rate = 0
        hot_rate_per_hr[i] = avg_hot_rate

    topic.hot_rate_per_hr = hot_rate_per_hr
    session_db.add(topic)
    session_db.commit()


# 更新所有topic的post_freq_per_hr属性
def update_topics_hot_rate_per_hr(session_db):
    topics = session_db.query(Topic).all()
    for topic in topics:
        update_topic_hot_rate_per_hr(session_db, topic.uuid)
    session_db.commit()


# 舆情预测，更新所有topic的stage字段
def update_topics_stage(session_db):
    topics = session_db.query(Topic).all()
    avg_hot_rate = sum(topic.hot_rate for topic in topics) / len(topics)

    for topic in topics:
        if not topic.hot_rate_per_hr:
            topic.stage = 1  # 设为潜伏期
            continue

        hot_rates = list(topic.hot_rate_per_hr.values())
        last_12_hr_hot_rates = hot_rates[-4:]  # 过去12小时的热度
        first_24_hr_hot_rates = hot_rates[:-8]  # 24小时之前的热度

        # 如果话题在过去的12小时内每小时的热度全部高于avg_hot_rate，那么判定该话题属于高潮期
        if all(rate > avg_hot_rate for rate in last_12_hr_hot_rates):
            topic.stage = 3  # 高潮期
        # 如果该话题的热度有高于avg_hot_rate的时间段，但是这些时间段全部位于24小时前，那么判定该话题属于衰退期
        elif any(rate > avg_hot_rate for rate in first_24_hr_hot_rates) and all(rate <= avg_hot_rate for rate in
                                                                                last_12_hr_hot_rates):
            topic.stage = 4  # 衰退期
        # 如果该话题的热度没有高于avg_hot_rate的时间段，那么判定该话题属于潜伏期
        elif all(rate <= avg_hot_rate for rate in hot_rates):
            topic.stage = 1  # 潜伏期
        # 否则，判定该话题为成长期
        else:
            topic.stage = 2  # 成长期

    session_db.commit()
