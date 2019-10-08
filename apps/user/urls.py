from django.conf.urls import url
from user.views import RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, UserOrderView, AddressView

# from user import views

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'), #注册
    url(r'^active/(.*)$', ActiveView.as_view(), name='active'), #用户激活
    url(r'^login$', LoginView.as_view(), name='login'), #登陆页面
    url(r'^logout$', LogoutView.as_view(), name='logout'), #退出页面
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'), #用户中心--订单
    url(r'^address$', AddressView.as_view(), name='address'), #用户中心--地址
    url(r'^$', UserInfoView.as_view(), name='user'), #用户中心--信息页

]
