from celery import Celery
from django.core.mail import send_mail
from django.template import loader, RequestContext

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

#创建Celery实力对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')

#定义发任务函数

@app.task
def send_active_mail(email, username, token):
    '''发送激活邮件'''
    subject = '天天生鲜欢迎信息'
    message = ''
    html_message = '<h1>%s,欢迎您，请点击下面连接激活您的账户</h1></br><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
    username, token, token)
    sender = '天天生鲜<18702644975@163.com>'
    receiver = [email]

    send_mail(subject, message, sender, receiver, html_message=html_message)


@app.task
def set_static_index_html():
    # 获取商品种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        type.image_banners = image_banners
        type.title_banners = title_banners

    # 组织模板上下文
    context = {
        'types': types,
        'goods_banners': goods_banners,
        'promotion_banners': promotion_banners,
    }

    #使用模板
    #加载模板文件
    temp = loader.get_template('static_index.html')
    #模板渲染
    static_index_html = temp.render(context)

    #生成首页静态文件
    with open('static/index.html', 'w') as f:
        f.write(static_index_html)






