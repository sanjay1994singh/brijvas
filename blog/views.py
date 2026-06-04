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
    blogs = Blog.objects.filter(
        is_published=True
    ).select_related(
        "category",
        "author"
    )

    categories = BlogCategory.objects.all()

    paginator = Paginator(
        blogs,
        9
    )

    page = request.GET.get("page")

    blogs = paginator.get_page(page)

    context = {

        "blogs": blogs,

        "categories": categories,

    }

    return render(
        request,
        "blog/blog_list.html",
        context
    )


def blog_detail(
        request,
        slug
):
    blog = get_object_or_404(

        Blog,

        slug=slug,

        is_published=True

    )

    blog.views += 1

    blog.save(
        update_fields=["views"]
    )

    related_blogs = Blog.objects.filter(

        category=blog.category,

        is_published=True

    ).exclude(

        id=blog.id

    )[:6]

    comments = BlogComment.objects.filter(

        blog=blog,

        is_approved=True

    ).order_by(

        "-created_at"

    )

    context = {

        "blog": blog,

        "related_blogs": related_blogs,

        "comments": comments,

    }

    return render(

        request,

        "blog/blog_detail.html",

        context

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
