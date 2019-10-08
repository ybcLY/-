from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.core.mail import send_mail
from celery_tasks.tasks import send_active_mail
from user.models import User, Address
from django.contrib.auth import authenticate, login, logout
from utills.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from django.core.paginator import Paginator

import re

# Create your views here.


#/user/register
def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        #接受数据
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        #校验数据
        if not all([username, pwd, email]):
            return render(request, 'register.html', {'msg': '数据不完整'})

        if allow != 'on':
            return render(request, 'register.html', {'msg': '请同意协议'})

        #校验用户名是否iu重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            #用户名存在
            return render(request, 'register.html', {'msg': '用户名已存在'})

        #进行业务处理
        user = User.objects.create_user(username, email, pwd)
        user.is_active = 0
        user.save()

        #返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class RegisterView(View):
    def get(self, request):
        '''显示页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''注册处理'''
        # 接受数据
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 校验数据
        if not all([username, pwd, email]):
            return render(request, 'register.html', {'msg': '数据不完整'})

        if allow != 'on':
            return render(request, 'register.html', {'msg': '请同意协议'})

        # 校验用户名是否iu重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            # 用户名存在
            return render(request, 'register.html', {'msg': '用户名已存在'})

        # 进行业务处理
        user = User.objects.create_user(username, email, pwd)
        user.is_active = 0
        user.save()

        #发送激活邮件

        #加密
        serializer = Serializer('sjkyvhsjn993nvks', 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info) #bytes
        token = token.decode('utf8')

        # 发邮件
        send_active_mail.delay(email, username, token)

        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):
    def get(self, request, token):
        '''用户激活'''
        # 进行解密
        serializer = Serializer('sjkyvhsjn993nvks', 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            #跳转到登陆页面
            return redirect(reverse('user:login'))

        except SignatureExpired:
            # 激活连接以过期
            return HttpResponse('激活连接以过期')


class LoginView(View):
    def get(self, request):
        '''登陆页面'''
        #判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        '''登陆校验'''

        #接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')

        #校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        #业务处理
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)

                #获取登陆后要跳转的地址,默认跳转到主页
                next_url = request.GET.get('next', reverse('goods:index'))

                response = redirect(next_url)

                #判断是否要记住用户名
                if remember == 'on':
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                return response
            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})
        else:
            #用户或密码错误
            return render(request, 'login.html', {'errmsg': '用户或密码错误'})


#/user/logout
class LogoutView(View):
    '''退出登陆'''
    def get(self, request):
        #清除用户session信息
        logout(request)

        #跳转到首页
        return redirect(reverse('goods:index'))



#/user
class UserInfoView(LoginRequiredMixin, View):
    '''用户中心----信息页'''
    def get(self, request):

        #获取个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        #获取用户历史浏览记录
        con = get_redis_connection('default')
        history_key = 'history_%d'%user.id

        #获取用户最新浏览的五个商品的id
        sku_ids = con.lrange(history_key, 0, 4)

        #从数据库中查询用户浏览的商品的具体信息
        goods_lis = []
        for sku_id in sku_ids:
            goods = GoodsSKU.objects.get(id=sku_id)
            goods_lis.append(goods)


        return render(request, 'user_center_info.html', {'page': 'user', 'address': address, 'goods_lis': goods_lis})


#/user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心----订单页'''
    def get(self, request, page):
        user = request.user

        #获取用户订单
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            #遍历order_skus计算商品小计
            for order_sku in order_skus:
                amount = order_sku.count*order_sku.price
                order_sku.amount = amount
            order.order_skus = order_skus

        #保存订单状态货到付款', '微信支付', '支付宝','银联支付'
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 对数据进行分页
        paginator = Paginator(orders, 1)

        # 获取page页内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取page页的实例对象
        order_page = paginator.page(page)

        context = {
            'order_page': order_page,
            'page': 'order'
        }




        return render(request, 'user_center_order.html', context)


#/user/address
class AddressView(LoginRequiredMixin, View):
    '''用户中心----地址页'''
    def get(self, request):
        #获取用户的收货地址
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     #不存在默认收货地址
        #     address = None
        address = Address.object.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        '''地址的添加'''
        #接受数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        #校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        #校验手机号
        if not re.match(r'^1[3|4|5|7|8|9][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号格式不对'})

        #业务处理
        user = request.user
        address = Address.object.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        #添加地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default
        )
        return redirect(reverse('user:address'))










