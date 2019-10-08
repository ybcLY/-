from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection
from order.models import OrderGoods
from django.core.paginator import Paginator

from django_redis import get_redis_connection
from django.core.cache import cache

# Create your views here.


class IndexView(View):
    '''首页'''
    def get(self, request):
        #从缓存中获取数据
        context = cache.get('index_page_data')

        if context is None:
            #获取商品种类信息
            types = GoodsType.objects.all()

            #获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            #获取首页促销信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            #获取首页分类商品展示信息
            for type in types:
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                type.image_banners = image_banners
                type.title_banners = title_banners

            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners
            }

            # 设置缓存
            cache.set('index_page_data', context, 3600)

        #获取购物车中商品的数目
        cart_count = 0
        user = request.user
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        #组织模板上下文
        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)


#/goods/good_id
class DetailView(View):
    '''详情页'''
    def get(self, request, good_id):
        try:
            sku = GoodsSKU.objects.get(id=good_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))


        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取商品评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        #获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        #获取同一SPU的商品年
        same_spu = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=good_id)

        # 获取购物车中商品的数目
        cart_count = 0
        user = request.user
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            #添加用户历史浏览记录
            history_key = 'history_%d'%user.id
            conn.lrem(history_key, 0, good_id)
            #从左侧插入
            conn.lpush(history_key, good_id)
            #只保存五条记录
            conn.ltrim(history_key, 0, 4)

        context = {
            'sku': sku,
            'types': types,
            'sku_order': sku_orders,
            'new_skus': new_skus,
            'same_spu': same_spu,
            'cart_count': cart_count
        }

        return render(request, 'detail.html', context)


#种类 排序方式 页码
#/list/id/页码?sort=排序方式
class ListView(View):
    '''列表页'''
    def get(self, request, type_id, page):

        #获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        #获取商品分类
        types = GoodsType.objects.all()

        #默认排序sort=default
        #价格排序sort=price
        #人气排序sort=hot
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=types).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=types).order_by('sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=types).order_by('id')

        #对数据进行分页
        paginator = Paginator(skus, 1)

        #获取page页内容
        try:
            page = int(page)
        except Exception as e:
           page = 1

        if page > paginator.num_pages:
            page = 1

        #获取page页的实例对象
        skus_page = paginator.page(page)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取购物车中商品的数目
        cart_count = 0
        user = request.user
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        #组织模板上下文
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'sort': sort,
            'cart_count': cart_count
        }


        return render(request, 'list.html', context)





















