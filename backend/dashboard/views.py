from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alertas.generacion import generar_alertas
from alertas.serializers import AlertaSerializer

from . import calculos


class ResumenDashboardView(APIView):
    """
    Panel principal (el número de caso de uso todavía no está definido).

        GET /api/dashboard/resumen/

    Devuelve en una sola respuesta todo lo que muestra la pantalla: los
    indicadores del día, la producción de la última semana, el stock de
    productos y las alertas recientes. Es una sola petición y no cinco porque
    es la primera pantalla que se abre al entrar al sistema.

    Permisos: cualquier usuario autenticado. Lo que ve el Operario queda
    limitado a sus galpones asignados (F-32); el stock de productos es de toda
    la granja, como en el listado de productos.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Las alertas se ponen al día antes de contarlas y mostrarlas.
        generar_alertas()
        datos = calculos.resumen(request.user)
        datos["alertas"] = AlertaSerializer(datos["alertas"], many=True).data
        return Response(datos)
