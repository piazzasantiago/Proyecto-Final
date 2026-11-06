from rest_framework.pagination import PageNumberPagination


class PaginacionListado(PageNumberPagination):
    """
    Paginación de los listados de la interfaz: 16 registros por página, lo que
    entra en pantalla junto al panel de detalle sin scroll largo.

    El cliente puede pedir otro tamaño con ?page_size=N (máximo 100), útil para
    los selectores que necesitan traer todos los registros.
    """

    page_size = 16
    page_size_query_param = "page_size"
    max_page_size = 100
