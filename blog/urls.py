from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.blog_list,
        name="blog_list"
    ),

    path(
        "search/",
        views.blog_search,
        name="blog_search"
    ),

    path(
        "category/<slug:slug>/",
        views.category_blogs,
        name="category_blogs"
    ),

    path(
        "comment/<int:blog_id>/",
        views.add_comment,
        name="add_comment"
    ),

    path(
        "<slug:slug>/",
        views.blog_detail,
        name="blog_detail"
    ),

]
