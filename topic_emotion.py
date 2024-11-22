from collections import defaultdict
import jieba
import pandas as pd
from data_analysis import get_blogposts_for_topic
from models import Topic


# 读取情感词典
def load_emotion_dict(filepath):
    emotion_df = pd.read_excel(filepath)  # 通过 pd.read_excel() 函数读取指定路径下的 Excel 文件
    emotion_dictionary = {}  # 创建一个空字典，用来存储情感词典数据
    for _, row in emotion_df.iterrows():  # 使用 emotion_df.iterrows() 迭代每一行数据
        word = row['词语']  # 获取当前行中的词语列的值，存储在变量 word 中
        emotion = row['情感分类']  # 获取当前行中的情感分类列的值，存储在变量 emotion 中
        intensity = row['强度']  # 获取当前行中的强度列的值，存储在变量 intensity 中
        emotion_dictionary[word] = {'情感分类': emotion, '强度': intensity}  # 将词语、情感分类和强度存储在 emotion_dict 字典中
    return emotion_dictionary  # 返回完整的情感词典字典


# 调用 load_emotion_dict 函数，传入 Excel 文件的路径作为参数，加载情感词典数据
emotion_dict = load_emotion_dict("emotionDict.xlsx")


# 使用情感词典进行情感分析
def analyze_sentiment(words):
    # 初始化一个字典来存储每个情感的总强度
    emotion_intensity = {}

    # 初始化输入文本的总强度
    total_intensity = 0

    # 初始化emotion_proportions为空字典
    emotion_proportions = {}

    # 遍历分词后的单词列表
    for word in words:
        # 先判断单词是否在情感词典中
        if word in emotion_dict:
            values = emotion_dict[word]
            emotion = values['情感分类']
            intensity = values['强度']

            # 将当前单词的强度值累加到总强度
            total_intensity += intensity

            # 将相同情感的强度值叠加起来
            if emotion in emotion_intensity:
                emotion_intensity[emotion] += intensity
            else:
                emotion_intensity[emotion] = intensity

        # 计算每个情感类别在总强度中的比例
        emotion_proportions = {emotion: intensity / total_intensity for emotion, intensity in emotion_intensity.items()}

    return emotion_proportions


# 对文本进行分词
def segment_text(text):
    return list(jieba.cut(text))


def calculate_average_emotions(session_db, topic_uuid):
    blogposts = get_blogposts_for_topic(session_db, topic_uuid)
    if not blogposts:
        return {}

    total_emotions = defaultdict(float)
    emotion_counts = defaultdict(int)

    for bp in blogposts:
        for emotion, intensity in bp.emotion.items():
            total_emotions[emotion] += intensity
            emotion_counts[emotion] += 1

    average_emotions = {emotion: total_emotions[emotion] / emotion_counts[emotion] for emotion in total_emotions}
    return average_emotions


# 对所有topic的emotion进行更新
def update_topics_emotions(session_db):
    topics = session_db.query(Topic).all()
    for topic in topics:
        topic.emotion = calculate_average_emotions(session_db, topic.uuid)
    session_db.commit()
