from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.core.paginator import Paginator
from django.db.models import Q

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import (
    Blog,
    BlogCategory,
    BlogComment
)


def blog_list(request):
    posts = Blog.objects.filter(
        is_published=True
    ).order_by('-created_at')

    paginator = Paginator(posts, 9)

    page = request.GET.get('page')

    posts = paginator.get_page(page)

    return render(
        request,
        'blog/blog_list.html',
        {
            'posts': posts
        }
    )


def blog_detail(request, slug):
    post = get_object_or_404(
        Blog,
        slug=slug,
        is_published=True
    )

    post.views += 1
    post.save()

    related_posts = Blog.objects.filter(
        category=post.category,
        is_published=True
    ).exclude(
        id=post.id
    )[:3]

    return render(
        request,
        "blog/blog_detail.html",
        {
            "post": post,
            "related_posts": related_posts
        }
    )


def blog_search(request):
    query = request.GET.get(
        "q"
    )

    blogs = Blog.objects.filter(
        is_published=True
    )

    if query:
        blogs = blogs.filter(

            Q(title__icontains=query)

            |

            Q(content__icontains=query)

        )

    paginator = Paginator(
        blogs,
        9
    )

    page = request.GET.get(
        "page"
    )

    blogs = paginator.get_page(
        page
    )

    context = {

        "blogs": blogs,

        "query": query

    }

    return render(

        request,

        "blog/blog_list.html",

        context

    )


def category_blogs(
        request,
        slug
):
    category = get_object_or_404(

        BlogCategory,

        slug=slug

    )

    blogs = Blog.objects.filter(

        category=category,

        is_published=True

    )

    paginator = Paginator(
        blogs,
        9
    )

    page = request.GET.get(
        "page"
    )

    blogs = paginator.get_page(
        page
    )

    context = {

        "category": category,

        "blogs": blogs,

    }

    return render(

        request,

        "blog/category_blogs.html",

        context

    )


@login_required
def add_comment(
        request,
        blog_id
):
    blog = get_object_or_404(
        Blog,
        id=blog_id
    )

    if request.method == "POST":
        comment = request.POST.get(
            "comment"
        )

        BlogComment.objects.create(

            blog=blog,

            user=request.user,

            comment=comment

        )

        messages.success(

            request,

            "Comment submitted successfully."

        )

    return redirect(
        "blog_detail",
        slug=blog.slug
    )
