from db_operations import clean_old_blogposts, update_topics_all
from models import BlogPost, Channel, Weight, Topic
from models import Session, SessionCopy
from spider import multi_spider
from data_preprocessing import merge_topics


# 初始没有数据库，进行初始化
def init():
    multi_spider(Session)
    merge_topics(Session)  # 数据预处理
    update_topics_all(Session)
    # 复制原来的数据到一个新的数据库，更新在新数据库中进行
    copy_database(Session, SessionCopy)


# 后续数据库更新
def update():
    # 清理过期数据
    clean_old_blogposts(SessionCopy)
    # 增加新数据
    multi_spider(SessionCopy)
    merge_topics(SessionCopy)
    update_topics_all(SessionCopy)
    # 更新数据库，合并为新数据库
    copy_database(SessionCopy, Session)


# 数据库复制
def copy_database(SessionSrc, SessionDst):
    src_session = SessionSrc()
    dst_session = SessionDst()

    # 清空目标数据库中的数据
    dst_session.query(BlogPost).delete()
    dst_session.query(Channel).delete()
    dst_session.query(Weight).delete()
    dst_session.query(Topic).delete()
    dst_session.commit()

    # 复制BlogPost数据
    blogposts = src_session.query(BlogPost).all()
    for post in blogposts:
        new_post = BlogPost(
            id=post.id,
            username=post.username,
            text=post.text,
            date=post.date,
            reposts_count=post.reposts_count,
            comments_count=post.comments_count,
            likes_count=post.likes_count,
            topics=post.topics,
            keywords=post.keywords,
            emotion=post.emotion
        )
        dst_session.add(new_post)
    dst_session.commit()

    # 复制Channel数据
    channels = src_session.query(Channel).all()
    for channel in channels:
        new_channel = Channel(
            title=channel.title,
            gid=channel.gid,
            containerid=channel.containerid
        )
        dst_session.add(new_channel)
    dst_session.commit()

    # 复制Weight数据
    weights = src_session.query(Weight).all()
    for weight in weights:
        new_weight = Weight(
            id=weight.id,
            post_count_weight=weight.post_count_weight,
            avg_likes_weight=weight.avg_likes_weight,
            avg_comments_weight=weight.avg_comments_weight,
            avg_reposts_weight=weight.avg_reposts_weight
        )
        dst_session.add(new_weight)
    dst_session.commit()

    # 复制Topic数据
    topics = src_session.query(Topic).all()
    for topic in topics:
        new_topic = Topic(
            topic_title=topic.topic_title,
            uuid=topic.uuid,
            stage=topic.stage,
            post_count=topic.post_count,
            keywords=topic.keywords,
            post_keywords=topic.post_keywords,
            hot_rate=topic.hot_rate,
            blogposts=topic.blogposts,
            emotion=topic.emotion,
            avg_likes=topic.avg_likes,
            avg_comments=topic.avg_comments,
            avg_reposts=topic.avg_reposts,
            hot_rate_per_hr=topic.hot_rate_per_hr
        )
        dst_session.add(new_topic)
    dst_session.commit()

    src_session.close()
    dst_session.close()
    print("成功复制数据库")


def main():
    while True:
        update()


if __name__ == "__main__":
    main()