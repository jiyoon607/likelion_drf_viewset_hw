from rest_framework.response import Response
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action

from .permissions import IsOwnerOrReadOnly
from .models import Post, Comment, Tag
from .serializers import PostSerializer, CommentSerializer, TagSerializer, PostListSerializer

from django.shortcuts import get_object_or_404

# Create your views here.
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    
    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer
    
    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action in ["update", "destroy", "partial_update", "likes"]:
            return [IsOwnerOrReadOnly()]
        return []

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        post = serializer.instance
        self.handle_tag(post)
        
        return Response(serializer.data)

    def perform_update(self, serializer):
        post = serializer.save()
        post.tag.clear()
        self.handle_tag(post)

    def handle_tag(self, post):
        tags = [word[1:] for word in post.content.split(' ') if word.startswith('#')]
        for t in tags:
            tag, created = Tag.objects.get_or_create(name=t)
            post.tag.add(tag)
        post.save()

    @action(methods=['GET'], detail=False)
    def likesTop3(self, request):
        top_posts = self.get_queryset().order_by("-likes_num")[:3]
        top_posts_serializer = PostListSerializer(top_posts, many=True)
        return Response(top_posts_serializer.data)
    
    @action(methods=['POST'], detail=True)
    def likes(self, request, pk=None):
        like_post = self.get_object()
        if request.user in like_post.like.all():
            like_post.like.remove(request.user)
            like_post.likes_num -= 1
        else:        
            like_post.like.add(request.user)
            like_post.likes_num += 1
        like_post.save(update_fields=["likes_num"])
        return Response()


class CommentViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in ["update", "destroy", "partial_update"]:
            return [IsOwnerOrReadOnly()]
        return []

class PostCommentViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin):
    serializer_class = CommentSerializer
    permissions_classes = [IsAuthenticated]

    def get_queryset(self):
        post = self.kwargs.get("post_id")
        queryset = Comment.objects.filter(post_id=post)
        return queryset

    def create(self, request, post_id=None):
        post = get_object_or_404(Post, id=post_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response(serializer.data)

class TagViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = "name"
    lookup_url_kwarg = "tag_name"

    def retrieve(self, request, *args, **kwargs):
        tag_name = kwargs.get("tag_name")
        tag = get_object_or_404(Tag, name=tag_name)
        posts = Post.objects.filter(tag=tag)
        serializer = MovieSerializer(posts, many=True)
        return Response(serializer.data)
        