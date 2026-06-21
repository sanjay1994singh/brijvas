from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from difflib import SequenceMatcher

from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import (
    Blog,
    BlogCategory,
    BlogComment
)
from core.seo import seo_slugify


def _slug_similarity(left, right):
    left = str(left or "").strip("-")
    right = str(right or "").strip("-")

    if not left or not right:
        return 0

    ratio = SequenceMatcher(None, left, right).ratio()
    left_tokens = {token for token in left.split("-") if len(token) > 2}
    right_tokens = {token for token in right.split("-") if len(token) > 2}

    if not left_tokens or not right_tokens:
        return ratio

    overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    return (ratio * 0.65) + (overlap * 0.35)


def _find_similar_blog_by_slug(slug):
    requested_slug = seo_slugify(
        slug,
        fallback="blog",
        max_length=120
    )

    best_post = None
    best_score = 0

    posts = Blog.objects.filter(
        is_published=True
    ).select_related(
        "category"
    ).only(
        "id",
        "title",
        "slug",
        "category__name"
    )

    for post in posts:
        candidate_text = " ".join(
            part for part in [
                post.title,
                getattr(post.category, "name", ""),
            ] if part
        )
        candidate_slug = seo_slugify(
            candidate_text,
            fallback=post.slug,
            max_length=120
        )

        score = max(
            _slug_similarity(requested_slug, post.slug),
            _slug_similarity(requested_slug, candidate_slug)
        )

        if score > best_score:
            best_score = score
            best_post = post

    if best_post and best_score >= 0.52:
        return best_post

    return None


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
    try:
        post = Blog.objects.get(
            slug=slug,
            is_published=True
        )
    except Blog.DoesNotExist:
        similar_post = _find_similar_blog_by_slug(slug)

        if similar_post:
            return redirect(
                "blog_detail",
                slug=similar_post.slug,
                permanent=True
            )

        raise Http404("No Blog matches the given query.")

    Blog.objects.filter(
        pk=post.pk
    ).update(
        views=F("views") + 1
    )
    post.views += 1

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
