from django.contrib import admin
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU, Goods
from django.core.cache import cache


class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''增加或更新表的数据时调用'''
        super().save_model(request, obj, form, change)
        # 发出任务让celery worker从新生成静态首页
        from celery_tasks.tasks import set_static_index_html
        set_static_index_html.delay()

        #清除缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '''删除表中的数据时调用'''
        super().save_model(request, obj)
        # 发出任务让celery worker从新生成静态首页
        from celery_tasks.tasks import set_static_index_html
        set_static_index_html.delay()

        # 清除缓存
        cache.delete('index_page_data')


class IndexPromotionBannerAdmin(BaseModelAdmin):
    list_display = ['id']


class GoodsTypeAdmin(BaseModelAdmin):
    list_display = ['id', 'name']


class IndexGoodsBannerAdmin(BaseModelAdmin):
    list_display = ['id']


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    list_display = ['id', 'display_type', 'index']






class GoodsSKUAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type']


class GoodsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(Goods, GoodsAdmin)







