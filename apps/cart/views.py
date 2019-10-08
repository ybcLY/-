from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse


from goods.models import GoodsSKU
from django_redis import get_redis_connection
from utills.mixin import LoginRequiredMixin
# Create your views here.

#/cart/add
class CartAddView(View):
    def post(self, request):
        '''添加购物车记录'''
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})
        #接受参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        #校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完正'})

        #检验数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数据出错'})

        #检验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        #业务处理,添加到购物车
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        #获取sku_id商品的值,没有会返回 None
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)

        #校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置sku_id商品的值
        conn.hset(cart_key, sku_id, count)

        #计算购物车商品的条目数
        total_count = conn.hlen(cart_key)

        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '添加成功'})


#/cart
class CartInfoView(LoginRequiredMixin, View):
    '''购物车页面显示'''
    def get(self, request):
        user = request.user

       #获取用户购物车商品信息
        cart_key = 'cart_%d'%user.id
        conn = get_redis_connection('default')
        cart_dict = conn.hgetall(cart_key)#{'商品id':'商品数量'}

        skus=[]
        total_count = 0
        total_price = 0
        #遍历获取
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            amount = sku.price*int(count)

            sku.count = count
            sku.amount = amount
            skus.append(sku)

            total_count += int(count)
            total_price += amount

        context = {
            'total_price': total_price,
            'total_count': total_count,
            'skus': skus
        }

        return render(request, 'cart.html', context)


#更新购物车记录
#/cart/update
class CartUpdateView(View):
    def post(self, request):
        '''#更新购物车记录'''
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})
        # 接受参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完正'})

        # 检验数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数据出错'})

        # 检验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理,添加到购物车
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        #更新
        conn.hset(cart_key, sku_id, count)

        #计算用户购物车的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '更新成功'})


#/cart/delete
class CartDeleteView(View):
    '''购物车记录删除'''
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登陆'})

        #接受参数
        sku_id = request.POST.get('sku_id')


        #检验数据
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '商品不存在'})

        #业务处理，删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        conn.hdel(cart_key, sku_id)

        # 计算用户购物车的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 2, 'total_count': total_count, 'errmsg': '用户未登陆'})
































