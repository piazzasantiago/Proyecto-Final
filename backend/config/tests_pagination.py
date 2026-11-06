"""Paginación de los listados: descartes, salidas, entradas, compras,
galpones, materias primas, proveedores, usuarios y productos.

Todos usan PaginacionListado: 16 por página, ?page_size= hasta 100 y
los filtros se aplican antes de paginar.
"""
import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from compras.models import Compra
from descartes.models import Descarte
from entradas.models import Entrada
from galpones.models import Galpon
from materias_primas.models import MateriaPrima
from productos.models import Producto
from proveedores.models import Proveedor
from salidas.models import Salida
from usuarios.models import Usuario

PASSWORD = "Pass1234!"
TOTAL = 20  # más que una página (16) y menos que dos


def crear_admin():
    u = Usuario(
        usuario="admin_pag", email="admin_pag@test.com", nombre="Admin",
        apellido="Pag", dni="70000000", rol=Usuario.ROL_ADMINISTRADOR,
    )
    u.set_password(PASSWORD)
    u.save()
    return u


def galpon(i):
    return Galpon.objects.create(
        galpon=f"Galpón {i:02d}", capacidad=100, superficie=10,
        latitud=-26.8, longitud=-65.2,
        estado=Galpon.ESTADO_INACTIVO if i < 3 else Galpon.ESTADO_ACTIVO,
    )


def ahora(i):
    return timezone.now() - datetime.timedelta(minutes=i)


class PaginacionBase:
    """Subclases definen `url`, `crear(i)`, `filtro` y `esperado_filtrado`."""

    url = None
    filtro = None            # querystring que deja solo algunos registros
    esperado_filtrado = None  # cuántos quedan con ese filtro
    existentes = 0           # registros que ya existen antes de crear TOTAL

    def crear(self, i):
        raise NotImplementedError

    def setUp(self):
        self.client = APIClient()
        self.admin = crear_admin()
        r = self.client.post(
            "/api/auth/login/",
            {"usuario": self.admin.usuario, "password": PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        for i in range(TOTAL):
            self.crear(i)
        self.total = TOTAL + self.existentes

    def test_primera_pagina_trae_16(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], self.total)
        self.assertEqual(len(r.data["results"]), 16)
        self.assertIsNotNone(r.data["next"])

    def test_ultima_pagina_trae_el_resto(self):
        r = self.client.get(self.url, {"page": 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), self.total - 16)
        self.assertIsNone(r.data["next"])

    def test_page_size_se_respeta(self):
        r = self.client.get(self.url, {"page_size": 5})
        self.assertEqual(len(r.data["results"]), 5)
        self.assertEqual(r.data["count"], self.total)

    def test_page_size_grande_trae_todo(self):
        r = self.client.get(self.url, {"page_size": 100})
        self.assertEqual(len(r.data["results"]), self.total)
        self.assertIsNone(r.data["next"])

    def test_paginas_no_se_repiten(self):
        a = self.client.get(self.url, {"page_size": 8, "page": 1}).data["results"]
        b = self.client.get(self.url, {"page_size": 8, "page": 2}).data["results"]
        c = self.client.get(self.url, {"page_size": 8, "page": 3}).data["results"]
        ids = [next(v for k, v in x.items() if k.startswith("id_")) for x in a + b + c]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), self.total)

    def test_pagina_inexistente_da_404(self):
        self.assertEqual(self.client.get(self.url, {"page": 99}).status_code, 404)

    def test_filtro_se_aplica_antes_de_paginar(self):
        if not self.filtro:
            self.skipTest("sin filtro simple")
        r = self.client.get(self.url, {**self.filtro, "page_size": 100})
        self.assertEqual(r.data["count"], self.esperado_filtrado)
        r = self.client.get(self.url, {**self.filtro, "page": 2})
        if self.esperado_filtrado <= 16:
            self.assertEqual(r.status_code, 404)
        else:
            self.assertEqual(len(r.data["results"]), self.esperado_filtrado - 16)


class PaginacionGalponesTests(PaginacionBase, TestCase):
    url = "/api/galpones/"
    filtro = {"estado": "I"}
    esperado_filtrado = 3

    def crear(self, i):
        galpon(i)


class PaginacionProductosTests(PaginacionBase, TestCase):
    url = "/api/productos/"
    filtro = {"estado": "I"}
    esperado_filtrado = 3

    def crear(self, i):
        Producto.objects.create(
            producto=f"Producto {i:02d}", stock_inicial=0,
            estado=Producto.ESTADO_INACTIVO if i < 3 else Producto.ESTADO_ACTIVO,
        )


class PaginacionMateriasPrimasTests(PaginacionBase, TestCase):
    url = "/api/materias-primas/"
    filtro = {"estado": "I"}
    esperado_filtrado = 3

    def crear(self, i):
        MateriaPrima.objects.create(
            materia_prima=f"Materia {i:02d}", unidad="kg", stock_inicial=0,
            estado=MateriaPrima.ESTADO_INACTIVO if i < 3 else MateriaPrima.ESTADO_ACTIVO,
        )


class PaginacionProveedoresTests(PaginacionBase, TestCase):
    url = "/api/proveedores/"
    filtro = {"estado": "I"}
    esperado_filtrado = 3

    def crear(self, i):
        Proveedor.objects.create(
            nombre=f"Proveedor {i:02d}", email=f"p{i}@test.com", telefono="381",
            estado=Proveedor.ESTADO_INACTIVO if i < 3 else Proveedor.ESTADO_ACTIVO,
        )


class PaginacionUsuariosTests(PaginacionBase, TestCase):
    url = "/api/usuarios/"
    existentes = 1  # el administrador que inicia sesión
    filtro = {"rol": Usuario.ROL_CONSULTA}
    esperado_filtrado = 20

    def crear(self, i):
        u = Usuario(
            usuario=f"user{i:02d}", email=f"user{i:02d}@test.com", nombre="N",
            apellido=f"A{i:02d}", dni=f"6000{i:04d}", rol=Usuario.ROL_CONSULTA,
        )
        u.set_password(PASSWORD)
        u.save()


class PaginacionEntradasTests(PaginacionBase, TestCase):
    url = "/api/entradas/"
    filtro = {"estado": "F"}
    esperado_filtrado = 3

    def crear(self, i):
        if i == 0:
            self.g = galpon(10)
        Entrada.objects.create(
            id_galpon=self.g, fecha=ahora(i),
            estado=Entrada.ESTADO_FINALIZADA if i < 3 else Entrada.ESTADO_PENDIENTE,
        )


class PaginacionSalidasTests(PaginacionBase, TestCase):
    url = "/api/salidas/"
    filtro = {"estado": "F"}
    esperado_filtrado = 3

    def crear(self, i):
        Salida.objects.create(
            fecha=ahora(i),
            estado=Salida.ESTADO_FINALIZADA if i < 3 else Salida.ESTADO_PENDIENTE,
        )


class PaginacionDescartesTests(PaginacionBase, TestCase):
    url = "/api/descartes/"
    filtro = {"categoria": Descarte.CATEGORIA_STOCK}
    esperado_filtrado = 3

    def crear(self, i):
        if i == 0:
            self.g = galpon(10)
        stock = i < 3
        Descarte.objects.create(
            categoria=Descarte.CATEGORIA_STOCK if stock else Descarte.CATEGORIA_GALPON,
            id_galpon=None if stock else self.g, fecha=ahora(i),
        )


class PaginacionComprasTests(PaginacionBase, TestCase):
    url = "/api/compras/"
    filtro = {"estado": "F"}
    esperado_filtrado = 3

    def crear(self, i):
        if i == 0:
            self.prov = Proveedor.objects.create(
                nombre="Prov", email="p@test.com", telefono="381"
            )
        Compra.objects.create(
            id_proveedor=self.prov, categoria="M",
            fecha=datetime.date.today(), estado="F" if i < 3 else "P",
        )
