from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Author, Book
from .permissions import IsOwnerOnly, IsOwnerOrModeratorOrReadOnly
from .serializers import AuthorSerializer, BookSerializer


class TokenLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        elif hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """Публічний довідник авторів: читати може будь-хто. Не змінюйте права тут."""

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsOwnerOrModeratorOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "author__name"]
    ordering_fields = ["price", "title"]

    def perform_create(self, serializer):
        owner = self.request.user if self.request.user.is_authenticated else None
        serializer.save(owner=owner)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsOwnerOnly],
        parser_classes=[MultiPartParser, FormParser],
    )
    def cover(self, request, pk=None):
        book = self.get_object()
        if "cover" not in request.data:
            return Response(
                {"cover": ["Файл обкладинки обов'язковий."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        book.cover = request.data["cover"]
        book.save()
        return Response(
            {"cover": request.build_absolute_uri(book.cover.url)},
            status=status.HTTP_200_OK,
        )
