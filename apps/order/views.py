from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.db import transaction

from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods

from django_redis import get_redis_connection
from utills.mixin import LoginRequiredMixin
from datetime import datetime
# Create your views here.


#/order/place
class OrderPlaceView(LoginRequiredMixin, View):
    '''订单页面显示'''
    def post(self, request):
        user = request.user

        #获取参数
        sku_ids = request.POST.getlist('sku_ids') #列表

        #检验参数
        if not sku_ids:
            '''跳转到购物车页面'''
            return redirect(reverse('cart:show'))

        # 业务处理

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        total_count = 0
        total_price = 0
        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            #计算小计
            amount = int(count)*sku.price

            sku.count = count
            sku.amount = amount
            total_count += int(count)
            total_price += amount

            skus.append(sku)

        #运费
        transit_price = 10

        #总付款

        total_pay = total_price + transit_price

        #获取用户的地址
        address = Address.objects.filter(user=user)

        sku_ids = ','.join(sku_ids)
        context = {
            'skus': skus,
            'total_price': total_price,
            'total_count': total_count,
            'transit_price' : transit_price,
            'total_pay': total_pay,
            'address': address,
            'sku_ids': sku_ids
        }
        return render(request, 'place_order.html', context)


class OrderCommitView(View):
    '''创建订单'''
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登陆'})

        #接受参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        #校验参数
        if not all[addr_id, pay_method, sku_ids]:
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        #校验支付
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '支付方式错误'})

        #校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址错误'})


        #业务处理,创建订单
        #向 df_order_info表中加记录
        #组织其参数
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        transit_price = 10
        total_count = 0
        total_price = 0

        #设置事务保存点
        save_p1 = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            for sku_id in sku_ids:
                #获取商品信息
                try:
                                                 #先加锁,事务结束锁释放
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(save_p1)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                count = conn.hget(cart_key, sku_id)
                # 向 df_order_goods添加记录
                #判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_p1)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                #更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                amount = sku.price*int(count)
                total_price += amount
                total_count += int(count)

            #更新订单信息表中的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_p1)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
        #提交事务
        transaction.savepoint_commit(save_p1)

        #清楚购物车中购买了的商品
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'res': 5, 'message': '创建成功'})














