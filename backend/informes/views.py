from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from galpones.models import Galpon
from materias_primas.models import MateriaPrima
from usuarios.permissions import LecturaAdministradorYConsulta_EscrituraAdministrador

from . import calculos, exportacion
from .calculos import parsear_id, parsear_periodo
FORMATOS = ("json", "xlsx", "pdf")


class InformeView(APIView):
    """
    Base de los informes: solo lectura para Administrador y Consulta
    (el Operario no tiene acceso a la sección).

    Cada informe se obtiene como JSON o, con `?formato=xlsx|pdf`, como archivo
    para descargar.
    """

    permission_classes = [LecturaAdministradorYConsulta_EscrituraAdministrador]

    def construir(self, params):  # pragma: no cover - lo define cada informe
        raise NotImplementedError

    def get(self, request):
        formato = request.query_params.get("formato", "json")
        if formato not in FORMATOS:
            raise ValidationError({"formato": "Formato inválido. Usá json, xlsx o pdf."})
        informe = self.construir(request.query_params)
        if formato == "json":
            return Response(informe)
        contenido, tipo = (
            (exportacion.a_xlsx(informe), exportacion.XLSX)
            if formato == "xlsx"
            else (exportacion.a_pdf(informe), exportacion.PDF)
        )
        respuesta = HttpResponse(contenido, content_type=tipo)
        respuesta["Content-Disposition"] = f'attachment; filename="{exportacion.nombre_archivo(informe, formato)}"'
        return respuesta


class InformeProduccionView(InformeView):
    """CU85 — Generar Informe de Producción. ?fecha_desde= &fecha_hasta= &id_galpon="""

    def construir(self, params):
        desde, hasta = parsear_periodo(params)
        galpon = parsear_id(params, "id_galpon", Galpon, "Galpón")
        return calculos.informe_produccion(desde, hasta, galpon)


class InformeLotesView(InformeView):
    """CU86 — Generar Informe de Lotes. ?estado=T|P|F &id_galpon="""

    def construir(self, params):
        estado = params.get("estado") or None
        if estado and estado not in ("T", "P", "F"):
            raise ValidationError({"estado": "Estado inválido. Usá T, P o F."})
        galpon = parsear_id(params, "id_galpon", Galpon, "Galpón")
        return calculos.informe_lotes(estado, galpon)


class InformeMateriasPrimasView(InformeView):
    """CU87 — Generar Informe de Materias Primas. ?fecha_desde= &fecha_hasta= &id_materia_prima="""

    def construir(self, params):
        desde, hasta = parsear_periodo(params)
        materia = parsear_id(params, "id_materia_prima", MateriaPrima, "Materia prima")
        return calculos.informe_materias_primas(desde, hasta, materia)


class InformeDescartesView(InformeView):
    """CU88 — Generar Informe de Descartes. ?fecha_desde= &fecha_hasta= &id_galpon= &tipo=G|M|P"""

    def construir(self, params):
        desde, hasta = parsear_periodo(params)
        galpon = parsear_id(params, "id_galpon", Galpon, "Galpón")
        tipo = params.get("tipo") or None
        if tipo and tipo not in calculos.TIPOS_DESCARTE:
            raise ValidationError({"tipo": "Tipo inválido. Usá G (gallinas), M (materia prima) o P (producto)."})
        return calculos.informe_descartes(desde, hasta, galpon, tipo)


class IndicadoresView(InformeView):
    """
    CU89 — Visualizar Indicadores Productivos.
    ?indicador=postura|mortandad|consumo &fecha_desde= &fecha_hasta= &id_galpon= &id_materia_prima=
    (id_materia_prima es obligatorio para el consumo). El valor objetivo lo define
    la pantalla: el backend solo entrega la serie real.
    """

    def construir(self, params):
        desde, hasta = parsear_periodo(params)
        galpon = parsear_id(params, "id_galpon", Galpon, "Galpón")
        materia = parsear_id(params, "id_materia_prima", MateriaPrima, "Materia prima")
        return calculos.indicadores(desde, hasta, params.get("indicador", "postura"), galpon, materia)
