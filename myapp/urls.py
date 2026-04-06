"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    path("index/",views.index,name="index"),
    path("shop/",views.shop,name="shop"),
    path("single/",views.single,name="single"),
    # path("single/<int:id>/",views.single,name="single"),
    path("bestseller/",views.bestseller,name="bestseller"),
    path("cart/", views.cart, name="cart"),
    path("add_to_cart/", views.add_to_cart, name="add_to_cart"),
    path("add_to_cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("update_cart/<int:item_id>/<str:action>/", views.update_cart, name="update_cart"),
    path("remove_from_cart/", views.remove_from_cart, name="remove_from_cart"),
    path("remove_from_cart/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("wishlist/", views.wishlist, name="wishlist"),
    # path("toggle_wishlist/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("compare/", views.compare, name="compare"),
    path("toggle_compare/<int:product_id>/", views.toggle_compare, name="toggle_compare"),
    # path("add-to-cart/<int:id>/", views.add_to_cart, name="add_to_cart"),
    # path("remove_from_cart/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cheackout/",views.cheackout,name="cheackout"),
    path("payment-success/", views.payment_success, name="payment_success"),
    path("error/",views.error,name="error"),
    path("contact/",views.contact,name="contact"),
    path("products/", views.product_list, name="products"),
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("forgot/",views.forgot,name="forgot"),
    path('apply_coupon/', views.apply_coupon, name='apply_coupon'),
    path("message/",views.message,name="message"),
    path("postreview/<int:product_id>/",views.postreview,name="postreview"),
    path("add_to_cart/", views.add_to_cart, name="add_to_cart"),
    path("add_to_wishlist/", views.add_to_wishlist, name="add_to_wishlist"),
]
