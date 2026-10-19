from django.urls import path

from .views import (
    IndicadoresView,
    InformeDescartesView,
    InformeLotesView,
    InformeMateriasPrimasView,
    InformeProduccionView,
)

urlpatterns = [
    path("informes/produccion/", InformeProduccionView.as_view(), name="informe-produccion"),
    path("informes/lotes/", InformeLotesView.as_view(), name="informe-lotes"),
    path("informes/materias-primas/", InformeMateriasPrimasView.as_view(), name="informe-materias-primas"),
    path("informes/descartes/", InformeDescartesView.as_view(), name="informe-descartes"),
    path("informes/indicadores/", IndicadoresView.as_view(), name="informe-indicadores"),
]
