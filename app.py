import sqlite3  # 连接数据库

import jieba  # 提供分词、识词过滤模块
import numpy as np  # 矩阵运算，中文显示需要运算空间
from PIL import Image  # 图像处理，如图形虚化、验证码、图片后期处理等
from flask import Flask, render_template, request  # Flask框架需要渲染页面用的库
from flask_caching import Cache  # Flask视图函数缓存，重复的数据，只需要缓存1次，10分钟自动清除缓存
from matplotlib import pyplot as plt  # 负责绘图的模块
from wordcloud import WordCloud  # 词云，形成有遮罩效果的图形

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


@app.route('/')  # 首页
def index():
    # 链接数据库
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    # 读取歌单、歌曲、评论总数、精彩评论总数
    sql = '''select * from count_all'''
    result_list = []
    table = cur.execute(sql)
    for row in table:
        result_list.append(row[0])
        result_list.append(row[1])
        result_list.append(row[2])
        result_list.append(row[3])
    # 随机读取两条精彩评论
    sql3 = '''select song_id,userAvatar,user_id,user_name,content,likeCount from comments_info where comment_type = 'hot_comments' and likeCount > 500 order by random() limit 4;'''
    table = cur.execute(sql3)
    datalist = []  # 存放每一行数据
    for row in table:
        data = {'song_id': row[0], 'userAvatar': row[1], 'user_id': row[2], 'user_name': row[3], 'content': row[4],
                'likeCount': row[5]}  # 利用字典存取数据比较方便
        datalist.append(data)
    cur.close()
    conn.close()
    print('打开index')
    return render_template('index.html', count=result_list, datalist=datalist)


@app.route('/refresh_index')  # 刷新首页的4个统计数据
def refresh_index():
    # 链接数据库
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    # 读取歌单、歌曲、评论总数
    result_list = []
    table = ['playlist', 'songs', 'comments_info', 'comments_info']
    column = ['list_id', 'song_id', 'comment_id', 'comment_id']
    for index in range(0, 3):
        table_name = table[index]
        column_name = column[index]
        sql1 = 'select count({column}) from (select * from {table} group by {column})'.format(table=table_name,
                                                                                              column=column_name)
        result = cur.execute(sql1)
        count = 0
        for r in result:
            for i in r:
                count = int(i)
        result_list.append(count)
    # 读取精彩评论条数
    table_name = table[3]
    column_name = column[3]
    where = 'comment_type = "hot_comments"'
    sql2 = 'select count({column}) from (select {column} from {table} where {where} group by {column})'.format(
        table=table_name,
        column=column_name,
        where=where)
    result = cur.execute(sql2)
    count = 0
    for r in result:
        for i in r:
            count = int(i)
    result_list.append(count)
    # 随机读取两条精彩评论
    sql3 = '''select song_id,userAvatar,user_id,user_name,content,likeCount from comments_info where comment_type = 'hot_comments' and likeCount > 500 order by random() limit 4;'''
    table = cur.execute(sql3)
    datalist = []  # 存放每一行数据
    for row in table:
        data = {'song_id': row[0], 'userAvatar': row[1], 'user_id': row[2], 'user_name': row[3], 'content': row[4],
                'likeCount': row[5]}  # 利用字典存取数据比较方便
        datalist.append(data)
    sql4 = '''update count_all set playlist_count={count}'''.format(count=result_list[0])
    cur.execute(sql4)
    sql4 = '''update count_all set songs_count={count}'''.format(count=result_list[1])
    cur.execute(sql4)
    sql4 = '''update count_all set comments_count={count}'''.format(count=result_list[2])
    cur.execute(sql4)
    sql4 = '''update count_all set hot_comment_count={count}'''.format(count=result_list[3])
    cur.execute(sql4)
    conn.commit()
    cur.close()
    conn.close()
    print('已刷新index')
    return render_template('index.html', count=result_list, datalist=datalist)


@app.route('/playlist')  # 歌单
@cache.cached(timeout=600)
def playlist():
    # 链接数据库
    data = {}  # 利用字典输入列名取数据，之后，再利用字典列名存数据
    datalist = []  # 每一条记录（字典）存到列表里，方面页面存取
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    key_list = ['list_img', 'list_url', 'list_name', 'list_tags', 'describe', 'built_time', 'star_count', 'share_count',
                'song_count', 'play_count', 'avatarUrl', 'author_url', 'author_name', 'level', 'followeds', 'signature',
                'province',
                'city', 'age', 'listenSongs', 'playlistCount', 'playlistBeSubscribedCount']
    for key in key_list:  # 给空字典添加key:value
        data[key] = ' '
    keys = ', '.join(key_list)  # select列名
    sql = 'select {keys} from playlist_info inner join author_info where userId = author_id  group by list_id order by random() limit 50'.format(
        keys=keys)
    result_list = cur.execute(sql)
    for row in result_list:
        # print(type(row), row)  # 可以见到每一行内容放在一个元组里
        data = {}  # 清空已存在的key:value
        for i in range(len(row)):
            data[key_list[i]] = row[i]
        datalist.append(data)
    cur.close()
    conn.close()
    for d in datalist:
        # 为了增加详情页，将song_id转换为字符串，用来做target标识，打开相应的详情页面
        d['target_id'] = str(d['list_url']).replace('https://music.163.com/playlist?id=', '')
        d['target_id'] = d['target_id'].replace('1', 'a').replace('2', 'b').replace('3', 'c').replace('4', 'd').replace(
            '5', 'e').replace('6', 'f').replace('7', 'g').replace('8', 'h').replace('9', 'i').replace('10', 'j')
        d['user_id'] = str(d['author_url']).replace('https://music.163.com/user/home?id=', '')
        d['user_id'] = d['user_id'].replace('1', 'a').replace('2', 'b').replace('3', 'c').replace('4', 'd').replace('5',
                                                                                                                    'e').replace(
            '6', 'f').replace('7', 'g').replace('8', 'h').replace('9', 'i').replace('10', 'j')
    return render_template('playlist_tables.html', datalist=datalist)


@app.route('/songs')  # 歌曲
@cache.cached(timeout=600)
def songs():
    # 链接数据库
    data = {}  # 利用字典输入列名取数据，之后，再利用字典列名存数据
    datalist = []  # 每一条记录（字典）存到列表里，方面页面存取
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    key_list = ['list_img', 'list_url', 'songs.song_id', 'song_url', 'song_name', 'song_duration', 'artists_name',
                'album_name', 'artists_id', 'album_size', 'album_id', 'album_img', 'publishTime', 'publishCompany',
                'publishSubType', 'lyric']
    for key in key_list:  # 给空字典添加key:value
        data[key] = ' '
    keys = ', '.join(key_list)  # select列名
    sql = '''select {keys} from playlist inner join songs inner join songs_info 
        where songs.song_id = songs_info.song_id and songs.list_id = playlist.list_id
        group by songs.song_id order by random() limit 50'''.format(keys=keys)
    result_list = cur.execute(sql)
    for row in result_list:
        # print(type(row), row)  # 可以见到每一行内容放在一个元组里
        data = {}  # 清空已存在的key:value
        for i in range(len(row)):
            data[key_list[i]] = row[i]
        datalist.append(data)
    cur.close()
    conn.close()
    for d in datalist:
        # 为了增加详情页，将song_id转换为字符串，用来做target标识，打开相应的详情页面
        d['target_id'] = str(d['songs.song_id']).replace('1', 'a').replace('2', 'b').replace('3', 'c').replace('4',
                                                                                                               'd').replace(
            '5', 'e').replace('6', 'f').replace('7', 'g').replace('8', 'h').replace('9', 'i').replace('10', 'j')
        d['lyric'] = d['lyric'].replace(u'\n', r'<br/>')
    return render_template('songs_tables.html', datalist=datalist)


@app.route('/comments')  # 评论
@cache.cached(timeout=600)
def comments():
    # 链接数据库
    data = {}  # 利用字典输入列名取数据，之后，再利用字典列名存数据
    datalist = []  # 每一条记录（字典）存到列表里，方面页面存取
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    key_list = ['userAvatar', 'user_name', 'level', 'user_id', 'song_id', 'totalCount', 'user_province',
                'user_city', 'user_introduce', 'createDays', 'ifOpenPlayRecord', 'comment_id', 'comment_type',
                'content',
                'beReplied_content', 'beR_userId', 'likeCount', 'comment_date', 'user_gender', 'user_age', 'createTime',
                'eventCount', 'follows', 'followeds', 'listenSongs', 'playlistCount', 'listBeStowCount']
    for key in key_list:  # 给空字典添加key:value
        data[key] = ' '
    keys = ', '.join(key_list)  # select列名
    sql = '''select {keys} from comments_info group by comment_id order by random() limit 50'''.format(keys=keys)
    result_list = cur.execute(sql)
    for row in result_list:
        # print(type(row), row)  # 可以见到每一行内容放在一个元组里
        data = {}  # 清空已存在的key:value
        for i in range(len(row)):
            data[key_list[i]] = row[i]
        datalist.append(data)
    cur.close()
    conn.close()
    for d in datalist:
        # 为了增加详情页，将song_id转换为字符串，用来做target标识，打开相应的详情页面
        d['user_gender'] = d['user_gender'].replace('0', '隐藏')
        d['ifOpenPlayRecord'] = str(d['ifOpenPlayRecord']).replace('0', '隐藏').replace('1', '公开')
        d['target_id'] = str(d['user_id']).replace('1', 'a').replace('2', 'b').replace('3', 'c').replace('4',
                                                                                                         'd').replace(
            '5', 'e').replace('6', 'f').replace('7', 'g').replace('8', 'h').replace('9', 'i').replace('10', 'j')
        d['comment_id'] = str(d['comment_id']).replace('1', 'a').replace('2', 'b').replace('3', 'c').replace('4',
                                                                                                             'd').replace(
            '5', 'e').replace('6', 'f').replace('7', 'g').replace('8', 'h').replace('9', 'i').replace('10', 'j')
        d['user_introduce'] = d['user_introduce'].replace(u'\n', '</br>')
    return render_template('comments_tables.html', datalist=datalist)


@app.route('/language_charts')
@cache.cached(timeout=600)
def language_charts():
    # 按照语种分布做图(6条线，歌单数量，歌曲数量，播放数量，收藏数量，分享数量，评论数量)
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    count_list = []  # 第1条线，存放某个语种的歌单数量
    count_song = []  # 第2条线，存放每个语种的歌曲数量
    count_play = []  # 第3条线，存放每个语种的播放总数量
    count_star = []  # 第4条线，存放每个语种的总收藏数量
    count_share = []  # 第5条线，存放每个语种的总分享数量
    count_comment = []  # 第6条线，存放每个语种的总评论数量(歌单)
    songs_language = ['日语', '粤语', '韩语', '欧美', '华语']
    for lan in songs_language:
        sql = '''
            select count(list_tags),sum(song_count),sum(play_count),sum(star_count),sum(share_count),sum(comment_count)
              from (select list_tags,star_count,share_count,comment_count,song_count,play_count 
                from playlist_info where list_tags like '%{lan}%');'''.format(lan=lan)
        table = cur.execute(sql)
        for row in table:
            count_list.append(row[0])
            count_song.append(row[1])
            count_play.append(row[2])
            count_star.append(row[3])
            count_share.append(row[4])
            count_comment.append(row[5])
    cur.close()
    conn.close()
    return render_template('language_charts.html', list_count=count_list, song_count=count_song, play_count=count_play,
                           star_count=count_star, share_count=count_share, comment_count=count_comment)


@app.route('/sentiment_charts')
@cache.cached(timeout=600)
def sentiment_charts():
    # 按照语种分布做图(6条线，歌单数量，歌曲数量，播放数量，收藏数量，分享数量，评论数量)
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    count_list = []  # 第1条线，存放某个情绪的歌单数量
    count_song = []  # 第2条线，存放每个情绪的歌曲数量
    count_play = []  # 第3条线，存放每个情绪的播放总数量
    count_star = []  # 第4条线，存放每个情绪的总收藏数量
    count_share = []  # 第5条线，存放每个情绪的总分享数量
    count_comment = []  # 第6条线，存放每个情绪的总评论数量(歌单)
    songs_sentiment = ['怀旧', '清新', '浪漫', '伤感', '治愈', '放松', '孤独', '感动', '兴奋', '快乐', '安静', '思念']
    for lan in songs_sentiment:
        sql = '''
            select count(list_tags),sum(song_count),sum(play_count),sum(star_count),sum(share_count),sum(comment_count)
              from (select list_tags,star_count,share_count,comment_count,song_count,play_count 
                from playlist_info where list_tags like '%{lan}%');'''.format(lan=lan)
        table = cur.execute(sql)
        for row in table:
            count_list.append(row[0])
            count_song.append(row[1])
            count_play.append(row[2])
            count_star.append(row[3])
            count_share.append(row[4])
            count_comment.append(row[5])
    cur.close()
    conn.close()
    return render_template('sentiment_charts.html', list_count=count_list, song_count=count_song, play_count=count_play,
                           star_count=count_star, share_count=count_share, comment_count=count_comment)


@app.route('/age_charts')
@cache.cached(timeout=600)
def age_charts():
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    # 读取用户年龄分布
    age = []
    age_count = []
    # 查询用户年龄分布的sql语句
    sql1 = '''select user_age,count(user_id) from comments_info where user_age > 0 group by user_age order by user_age;'''
    # 查询用户注册至今天数分布的sql语句
    table1 = cur.execute(sql1)
    for row in table1:
        age.append(row[0])
        age_count.append(row[1])
    # 关闭连接
    cur.close()
    conn.close()
    return render_template('age_charts.html', age=age, age_count=age_count)


@app.route('/days_charts')
@cache.cached(timeout=600)
def days_charts():
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    # 读取用户年龄分布
    # 读取用户注册天数分布
    days = []
    days_count = []
    sql2 = '''select createDays,count(user_id) from comments_info group by createDays order by createDays;'''
    table2 = cur.execute(sql2)
    for row in table2:
        days.append(row[0])
        days_count.append(row[1])
    # 关闭连接
    cur.close()
    conn.close()
    return render_template('days_charts.html', days=days, days_count=days_count)


@app.route('/listen_age_charts')
@cache.cached(timeout=600)
def listen_age_charts():
    """男女生: 年龄-听歌 散点分布图"""
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    # 读取用户年龄分布
    # 读取用户注册天数分布
    male_age_listen = []
    female_age_listen = []
    sql1 = '''select user_age,listenSongs from comments_info where user_age > 0 and user_age < 45 and user_gender = '男' and listenSongs < 50000 group by user_id limit 15000;'''
    sql2 = '''select user_age,listenSongs from comments_info where user_age > 0 and user_age < 45 and user_gender = '女' and listenSongs < 50000 group by user_id limit 15000;'''
    table1 = cur.execute(sql1)
    for row in table1:
        male_age_listen.append([row[1], row[0]])
    table2 = cur.execute(sql2)
    for row in table2:
        female_age_listen.append([row[1], row[0]])
    # 关闭连接
    cur.close()
    conn.close()
    return render_template('listen_age_charts.html', male=male_age_listen, female=female_age_listen)


@app.route('/all_lyric_word')
def all_lyric_word():
    word_frequency = 0  # 记录词频
    # 连接数据库，查询所有华语歌词的词频
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''select all_lyric_rate from count_all'''
    table = cur.execute(sql)
    for row in table:
        word_frequency = row[0]
    cur.close()
    conn.close()
    img_url = 'static/img/wordcloud/all_lyric_word_defult.jpg'
    return render_template('all_lyric_word.html', img_url=img_url, word_frequency=word_frequency)


@app.route('/refresh_all_lyric_word')
def refresh_all_lyric_word():
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''select lyric from songs_info
          inner join playlist_info
          inner join songs
          on songs.song_id = songs_info.song_id and songs.list_id = playlist_info.list_id
          where list_tags like '%华语%' or list_tags like '%粤语%' group by songs.song_id'''
    text = ""
    table = cur.execute(sql)
    for lyric in table:
        clean_text = lyric[0]
        clean_text = clean_text.replace('制作人', '').replace('作词', '').replace('编曲', '').replace('作曲', '') \
            .replace('和声', '').replace('演唱', '').replace('他', '').replace('我', '').replace('你', '') \
            .replace('的', '').replace('啦', '').replace('了', '').replace('们', '').replace(' ', '') \
            .replace('她', '').replace('这', '').replace('把', '').replace('啊', '').replace('是', '')
        text += clean_text
    cur.close()
    conn.close()
    print('已读取完所有歌词！准备分词')
    # jieba库将词拆分出来
    lyric_cut = jieba.cut(text)
    lyric_str = ' '.join(lyric_cut)  # 分词拼接
    word_frequency = len(lyric_str)  # 计算分词数量/词频
    img = Image.open('static/img/wordcloud/backgroud/bg_lyric.jpg')  # 打开遮罩图片
    img_array = np.array(img)  # 将图片转换为色块数组，进行计算
    wc = WordCloud(
        background_color='white',
        mask=img_array,
        font_path='msyh.ttc'
    )
    wc.generate_from_text(lyric_str)
    print(f'分词{word_frequency}完毕！准备绘制图片！')
    # 更新词频统计
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''update count_all set all_lyric_rate = {word_rate}'''.format(word_rate=word_frequency)
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print('已更新词频')
    # 绘制图片
    fig = plt.figure(1)
    plt.imshow(wc)
    plt.axis('off')
    # 保存图片
    plt.savefig('static/img/wordcloud/all_lyric_word_' + str(word_frequency) + '.jpg', dpi=500)
    print('图片已生成！请查看文件')
    img_url = 'static/img/wordcloud/all_lyric_word_' + str(word_frequency) + '.jpg'
    return render_template('all_lyric_word.html', img_url=img_url, word_frequency=word_frequency)


@app.route('/hot_comments_word')
def hot_com_word():
    word_frequency = 0  # 记录词频
    # 连接数据库，查询所有华语歌词的词频
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''select all_hot_com_rate from count_all'''
    table = cur.execute(sql)
    for row in table:
        word_frequency = row[0]
    cur.close()
    conn.close()
    img_url = 'static/img/wordcloud/hot_comments_word_defult.jpg'
    return render_template('hot_comments_word.html', img_url=img_url, word_frequency=word_frequency)


@app.route('/refresh_hot_com_word')
def refresh_hot_com_word():
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''select content from comments_info
              where comment_type = 'hot_comments' group by song_id'''
    text = ""
    table = cur.execute(sql)
    for lyric in table:
        clean_text = lyric[0]
        clean_text = clean_text.replace('制作人', '').replace('作词', '').replace('编曲', '').replace('作曲', '') \
            .replace('和声', '').replace('演唱', '').replace('他', '').replace('我', '').replace('你', '') \
            .replace('的', '').replace('啦', '').replace('了', '').replace('们', '').replace(' ', '') \
            .replace('她', '').replace('这', '').replace('把', '').replace('啊', '').replace('是', '')
        text += clean_text
    print('已读取完所有热评！准备分词')
    # jieba库将词拆分出来
    lyric_cut = jieba.cut(text)
    lyric_str = ' '.join(lyric_cut)  # 分词拼接
    word_frequency = len(lyric_str)  # 计算分词数量/词频
    img = Image.open('static/img/wordcloud/backgroud/bg_diy.jpg')  # 打开遮罩图片
    img_array = np.array(img)  # 将图片转换为色块数组，进行计算
    wc = WordCloud(
        background_color='white',
        mask=img_array,
        font_path='msyh.ttc'
    )
    wc.generate_from_text(lyric_str)
    print(f'分词{word_frequency}完毕！准备绘制图片！')
    # 更新词频统计
    sql = '''update count_all set all_hot_com_rate = {word_rate}'''.format(word_rate=word_frequency)
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print('已更新词频')
    # 绘制图片
    fig = plt.figure(1)
    plt.imshow(wc)
    plt.axis('off')
    # 保存图片
    plt.savefig('static/img/wordcloud/hot_comments_word_' + str(word_frequency) + '.jpg', dpi=500)
    print('图片已生成！请查看文件')
    img_url = 'static/img/wordcloud/hot_comments_word_' + str(word_frequency) + '.jpg'
    return render_template('hot_comments_word.html', img_url=img_url, word_frequency=word_frequency)


@app.route('/diy_song_word')
def diy_song_word():
    word_frequency = 0  # 记录词频
    # 连接数据库，查询所有华语歌词的词频
    conn = sqlite3.connect('data/NEC_Music.db')
    cur = conn.cursor()
    sql = '''select one_song_com_rate from count_all'''  # 读取上次onesong的词频
    table = cur.execute(sql)
    for row in table:
        word_frequency = row[0]
    cur.close()
    conn.close()
    img_url = 'static/img/wordcloud/diy_song_word_defualt.jpg'  # 显示默认图片
    return render_template('diy_song_word.html', img_url=img_url, word_frequency=word_frequency)


import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


@app.route('/refresh_diy_song_word', methods=['POST', 'GET'])
def refresh_diy_song_word():
    diy_song_name = '歌曲名'  # 保存用户输入的歌名关键词

    # 连接数据库
    with sqlite3.connect('data/NEC_Music.db') as conn:
        cur = conn.cursor()

        if request.method == 'POST':
            diy_song_name = request.form.get('关键词', '')  # 获取表单中的关键词
            print(request.form)

        # 执行 SQL 查询（改用参数化查询）
        sql = '''SELECT song_name, content FROM songs_info s
                 INNER JOIN comments_info ci ON s.song_id = ci.song_id
                 WHERE s.song_name LIKE ? GROUP BY content'''
        cur.execute(sql, ('%' + diy_song_name + '%',))
        rows = cur.fetchall()

        if not rows:
            # 如果没有找到相关评论内容，可以返回一个提示信息给用户或者做其他处理
            diy_song_name = diy_song_name + '--无歌词'
            return render_template('diy_song_word.html', diy_song_name=diy_song_name)

        print('开始读取并清洗歌词')
        text = ""
        for lyric in rows:
            clean_text = lyric[1]
            print('清洗前：', clean_text)
            clean_text = clean_text.replace('制作人', '').replace('作词', '').replace('编曲', '').replace('作曲', '') \
                .replace('和声', '').replace('演唱', '').replace('他', '').replace('我', '').replace('你', '') \
                .replace('的', '').replace('啦', '').replace('了', '').replace('们', '').replace(' ', '') \
                .replace('她', '').replace('这', '').replace('把', '').replace('啊', '').replace('是', '')
            print('清洗后：', clean_text)
            text += clean_text

        print('已读取完所有评论！准备分词')
        # jieba库将词拆分出来
        lyric_cut = jieba.cut(text)
        lyric_str = ' '.join(lyric_cut)  # 分词拼接
        word_frequency = len(lyric_str.split())  # 计算分词数量/词频

        # 更新词频统计
        sql_update = '''UPDATE count_all SET one_song_com_rate = ?'''
        cur.execute(sql_update, (word_frequency,))
        conn.commit()

        print(f'分词{word_frequency}完毕！准备绘制图片！')

        # 打开遮罩图片
        img = Image.open('static/img/wordcloud/backgroud/bg_song.jpg')
        img_array = np.array(img)  # 将图片转换为数组，进行计算

        # 生成词云
        wc = WordCloud(
            background_color='white',
            mask=img_array,
            font_path='msyh.ttc'
        )
        wc.generate_from_text(lyric_str)

        print('已更新词频')

        # 绘制图片
        plt.figure(1)
        plt.imshow(wc)
        plt.axis('off')

        # 保存图片
        img_filename = f'static/img/wordcloud/diy_song_word_{diy_song_name}.jpg'
        plt.savefig(img_filename, dpi=500)
        print(f'图片已生成！路径：{img_filename}')

        img_url = img_filename
        return render_template('diy_song_word.html', img_url=img_url, word_frequency=word_frequency,
                               diy_song_name=diy_song_name)


@app.route('/techno')
def techno():
    return render_template('techno.html')


@app.route('/team')
def team():
    return render_template('team.html')


if __name__ == '__main__':
    app.run()  # 不开调试模式

    # app.jinja_env.auto_reload = True
    # app.config['TEMPLATES_AUTO_RELOAD'] = True
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
    # app.run()
    # app.run(debug=True)
