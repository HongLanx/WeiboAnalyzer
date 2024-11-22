import base64
import json
import os
import sqlite3
from io import BytesIO

import dash
import pandas as pd
import plotly.express as px
from dash import dcc, html, Input, Output
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from plotly.graph_objs import Scatter
from wordcloud import WordCloud

# Flask 应用初始化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_random_secret_key_123456'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(os.path.dirname(__file__), "userinfo.db")}'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# 用户类，继承自 UserMixin 和 SQLAlchemy 模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


# Flask-Login 的用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 首页路由
@app.route('/')
def home():
    return render_template('home.html')


# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect('/dashboard')
        else:
            flash('错误的用户名或密码', 'danger')
    return render_template('login.html')


# 登出路由
@app.route('/logout')
@login_required  # 需要登录才能访问
def logout():
    logout_user()
    return redirect(url_for('home'))


# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('注册成功！', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


# 仪表板路由
@app.route('/dashboard')
@login_required  # 需要登录才能访问
def dashboard():
    return redirect('/dash_app')


# 从数据库生成词云图像的函数
def generate_wordcloud_from_db(db_path):
    conn = sqlite3.connect(db_path)
    query = "SELECT topic_title, post_count FROM topics"
    df = pd.read_sql(query, conn)
    conn.close()

    # 创建一个字典，其中键是话题标题，值是帖子数
    word_freq = dict(zip(df['topic_title'], df['post_count']))

    wordcloud = WordCloud(font_path='方正黑体_GBK.TTF', width=800, height=400,
                          background_color='white').generate_from_frequencies(word_freq)
    image_stream = BytesIO()
    wordcloud.to_image().save(image_stream, format='PNG')
    encoded_image = base64.b64encode(image_stream.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{encoded_image}'


# 从数据库生成关键词词云图像的函数
def generate_wordcloud_from_keywords(db_path, topic_title):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT post_keywords FROM topics WHERE topic_title=?", (topic_title,))
    post_keywords = cursor.fetchone()

    conn.close()

    if post_keywords:
        post_keywords = post_keywords[0]
        # 将 Unicode 编码转换为汉字
        post_keywords = post_keywords.encode('ascii').decode('unicode_escape')

        wordcloud = WordCloud(font_path='方正黑体_GBK.TTF', width=800, height=400,
                              background_color='white').generate(post_keywords)
        image_stream = BytesIO()
        wordcloud.to_image().save(image_stream, format='PNG')
        encoded_image = base64.b64encode(image_stream.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{encoded_image}'
    return None


# 从数据库生成时间序列数据的函数
def generate_time_series_data(db_path, category):
    conn = sqlite3.connect(db_path)
    query = "SELECT hot_rate_per_hr FROM topics WHERE topic_title = ?"
    df = pd.read_sql(query, conn, params=(category,))
    conn.close()

    if df.empty or df['hot_rate_per_hr'].iloc[0] is None:
        return pd.DataFrame({'Hour': [], 'Hot Rate': []})

    hot_rate_per_hr = eval(df['hot_rate_per_hr'].iloc[0])
    hours = [i * 3 for i in range(len(hot_rate_per_hr))]
    hot_rates = [hot_rate_per_hr[str(i)] for i in range(len(hot_rate_per_hr))]

    time_series_data = pd.DataFrame({'Hour': hours, 'Hot Rate': hot_rates})
    return time_series_data


# 从数据库生成情感数据的函数
def generate_sentiment_data(db_path, topic_title):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT emotion FROM topics WHERE topic_title=?", (topic_title,))
    emotion = cursor.fetchone()

    conn.close()

    if emotion:
        emotion = emotion[0]
        # 将 Unicode 编码转换为汉字
        emotion_dict = json.loads(emotion)
        decoded_emotion_dict = {key.encode('unicode_escape').decode('unicode_escape'): value for key, value in
                                emotion_dict.items()}
        return decoded_emotion_dict
    return {}


# 从数据库生成词频数据的函数
def generate_word_frequency_data(db_path, topic_title):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT post_keywords FROM topics WHERE topic_title=?", (topic_title,))
    post_keywords = cursor.fetchone()

    conn.close()

    if post_keywords:
        post_keywords = post_keywords[0]
        # 将 Unicode 编码转换为汉字
        keyword_dict = json.loads(post_keywords)
        decoded_keyword_dict = {str(key).encode('unicode_escape').decode('unicode_escape'): value for key, value in
                                keyword_dict.items()}
        return decoded_keyword_dict
    return {}


# 从数据库获取阶段文本的函数
def get_stage_text(db_path, topic_title):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT stage FROM topics WHERE topic_title=?", (topic_title,))
    stage_value = cursor.fetchone()

    conn.close()

    if stage_value:
        stage_value = stage_value[0]
        if stage_value == 1:
            return "潜伏期"
        elif stage_value == 2:
            return "成长期"
        elif stage_value == 3:
            return "高潮期"
        elif stage_value == 4:
            return "衰退期"
    return "未知阶段"


# 创建 Dash 应用程序
def create_dashboard(server):
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname='/dash_app/',
    )
    # 连接到 SQLite 数据库并检索数据
    conn = sqlite3.connect('weibo.db')
    query = "SELECT topic_title, hot_rate FROM topics"
    df = pd.read_sql_query(query, conn)
    conn.close()

    # 按热度排序并选择前10个话题
    df = df.sort_values(by='hot_rate', ascending=False).head(10)
    # 情感和词频图表的样本数据
    sentiment_data = {
        'Category': ['Positive', 'Negative', 'Neutral'],
        'Count': [20, 5, 10]
    }

    freq_data = {
        'Word': ['Python', 'Dash', 'Plotly', 'JavaScript', 'Java'],
        'Frequency': [50, 30, 25, 20, 15]
    }

    # 时间序列图的样本数据
    time_series_data = {
        'Date': pd.date_range('2023-01-01', periods=10),
        'Topic Heat': [30, 35, 40, 45, 50, 55, 60, 65, 70, 75]
    }

    # 内容样式，确保其在背景上方
    content_style = {
        'position': 'relative',
        'padding': '20px',
        'borderRadius': '5px',
        'color': 'white',
        'backgroundColor': 'rgba(0, 0, 0, 0.6)'  # 黑色带透明度的背景色，以提高可读性
    }

    # 主页面布局
    main_page_layout = html.Div(style=content_style, children=[
        html.H1("首页", style={'textAlign': 'center', 'color': '#fff'}),

        html.Div([
            html.H2('Bar Chart', style={'color': '#fff'}),
            dcc.Graph(
                id='bar-chart',
                figure={
                    'data': [
                        {'y': df['topic_title'], 'x': df['hot_rate'], 'type': 'bar', 'orientation': 'h',
                         'name': 'Topics', 'marker': {'color': '#ff9900'}
                         },
                    ],
                    'layout': {
                        'title': {
                            'text': '热门话题TOP10',
                            'font': {'size': 50, 'color': 'red', 'family': 'KaiTi'}
                        },
                        'plot_bgcolor': 'rgba(0,0,0,0)',
                        'paper_bgcolor': 'rgba(0,0,0,0)',
                        'font': {'color': '#fff'},
                        'yaxis': {'automargin': True, 'dtick': 1, 'tickfont': {'size': 20}},
                        'xaxis': {'tickfont': {'size': 20}},
                        'height': 800
                    }
                }
            )
        ], style={'backgroundColor': 'rgba(0,0,0,0.5)', 'padding': '20px', 'borderRadius': '5px'}),

        html.Div([
            html.H2("总话题词云图"),
            html.Img(src=generate_wordcloud_from_db(r'weibo.db'),
                     style={'width': '100%', 'height': '100%'})
        ], style={'backgroundColor': 'rgba(0,0,0,0.5)', 'padding': '20px', 'borderRadius': '5px'}),
    ])

    def detail_page_layout(category):
        time_series_data = generate_time_series_data(r'weibo.db', category)
        sentiment_data = generate_sentiment_data(r'weibo.db', category)
        word_frequency_data = generate_word_frequency_data(r'weibo.db', category)
        stage_text = get_stage_text(r'weibo.db', category)

        sentiment_df = pd.DataFrame(list(sentiment_data.items()), columns=['Emotion', 'Value'])
        word_frequency_df = pd.DataFrame(list(word_frequency_data.items()), columns=['Keyword', 'Frequency'])

        return html.Div(style=content_style, children=[
            html.H1(f"热点分析—— {category}", style={'textAlign': 'center', 'color': '#fff'}),

            html.Div(
                style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center',
                       'backgroundColor': 'rgba(0,0,0,0.5)', 'padding': '20px', 'borderRadius': '5px'},
                children=[
                    html.Div(
                        style={'textAlign': 'center'},
                        children=[
                            html.H2("词云图"),
                            html.Img(src=generate_wordcloud_from_keywords(r'weibo.db', category),
                                     style={'width': '100%', 'height': 'auto'})
                        ]
                    )
                ]
            ),

            dcc.Graph(
                id='sentiment-chart',
                figure=px.bar(
                    sentiment_df,
                    x='Emotion',
                    y='Value',
                    title='情感分析',
                    color='Emotion'  # 使用颜色区分不同的柱子
                ).update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font={'color': '#fff', 'size': 20},
                    yaxis=dict(range=[0, 1])  # 根据需要调整范围以便更好地可视化
                )
            ),

            dcc.Graph(
                id='word-frequency-chart',
                figure=px.bar(
                    word_frequency_df,
                    x='Keyword',
                    y='Frequency',
                    title='词频分析',
                    color='Keyword'  # 使用颜色区分不同的柱子
                ).update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font={'color': '#fff', 'size': 20}
                )
            ),

            dcc.Graph(
                id='time-series-chart',
                figure={
                    'data': [
                        Scatter(
                            x=time_series_data['Hour'],
                            y=time_series_data['Hot Rate'],
                            mode='lines+markers',
                            line_shape='spline',
                            line=dict(color='cyan')  # 设置曲线的颜色
                        )
                    ],
                    'layout': {
                        'title': '话题热度时间变化表',
                        'plot_bgcolor': 'rgba(0,0,0,0)',
                        'paper_bgcolor': 'rgba(0,0,0,0)',
                        'font': {'color': '#fff', 'size': 20}
                    }
                }
            ),

            html.Div([
                html.H2("舆情预测", style={'textAlign': 'center', 'fontSize': '40px', 'color': '#fff'}),
                html.P(stage_text, style={'textAlign': 'center', 'fontSize': '30px', 'color': '#fff'})
            ], style={'backgroundColor': 'rgba(0,0,0,0.5)', 'padding': '20px', 'borderRadius': '5px'})
        ])

    # 页面布局
    dash_app.layout = html.Div([
        dcc.Location(id='url', refresh=False),  # 跟踪URL
        html.Div(id='page-content')
    ], style={'position': 'relative', 'minHeight': '100vh',
              'backgroundImage': 'url(https://ts1.cn.mm.bing.net/th/id/R-C.24e96b1c7d473739362011b89886ca53?rik=kzBZPiDwI7rJ5g&riu=http%3a%2f%2fe0.ifengimg.com%2f01%2f2019%2f0413%2fDDF217E589518ADACFA188CA8B6CD8069BF235A7_size2089_w424_h231.gif&ehk=BA%2b%2biXuh1%2f%2fJKuzqGuYEKgl6CqtWHExZY7sOmOfyo2o%3d&risl=1&pid=ImgRaw&r=0)',
              'backgroundSize': 'cover', 'backgroundPosition': 'center', 'backgroundAttachment': 'fixed'})

    # 点击柱状图时更新URL回调
    @dash_app.callback(
        Output('url', 'pathname'),
        [Input('bar-chart', 'clickData')]
    )
    def update_url(click_data):
        if click_data:
            selected_category = click_data['points'][0]['y']
            return f"/detail/{selected_category}"
        return "/"

    # 渲染页面回调
    @dash_app.callback(
        Output('page-content', 'children'),
        [Input('url', 'pathname')]
    )
    def display_page(pathname):
        if pathname and pathname.startswith("/detail/"):
            selected_category = pathname.split("/")[-1]
            return detail_page_layout(selected_category)
        return main_page_layout

    return dash_app


# 启动 Flask 和 Dash 应用
dash_app = create_dashboard(app)

if __name__ == '__main__':
    app.run(debug=True)
