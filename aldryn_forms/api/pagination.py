from rest_framework import pagination


class AldrynFormsPagination(pagination.PageNumberPagination):
    """Set the maximum list size."""

    page_size = 50
