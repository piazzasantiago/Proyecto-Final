from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    """
    Django exige un manager propio cuando se reemplaza el modelo de usuario.
    Define cómo se crean usuarios normales y superusuarios.
    """

    def create_user(self, usuario, email, password=None, **extra_fields):
        if not usuario:
            raise ValueError("El nombre de usuario es obligatorio.")
        if not email:
            raise ValueError("El email es obligatorio.")

        user = self.model(usuario=usuario, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)  # hashea la contraseña, nunca se guarda en texto plano
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, email, password=None, **extra_fields):
        """
        Lo usa `python manage.py createsuperuser`.
        Un superusuario siempre es Administrador y puede entrar a /admin/.
        """
        extra_fields.setdefault("rol", Usuario.ROL_ADMINISTRADOR)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True.")

        return self.create_user(usuario, email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Corresponde a la tabla 'Usuarios' del modelo relacional:
    idUsuario INT PK, nombre VARCHAR(100), apellido VARCHAR(100),
    usuario VARCHAR(100), email VARCHAR(150), dni VARCHAR(15),
    contrasenia VARCHAR(255), rol CHAR(1), estado CHAR(1).

    El campo `contrasenia` del modelo relacional se implementa con el campo
    `password` que hereda de AbstractBaseUser: Django lo administra solo
    (hash, verificación, cambio) y guarda el hash, nunca la contraseña.

    Hereda de:
    - AbstractBaseUser: password, last_login y el manejo de sesión.
    - PermissionsMixin: is_superuser y los permisos que necesita /admin/.
    """

    ROL_ADMINISTRADOR = "A"
    ROL_OPERARIO = "O"
    ROL_CONSULTA = "C"
    ROL_CHOICES = [
        (ROL_ADMINISTRADOR, "Administrador"),
        (ROL_OPERARIO, "Operario"),
        (ROL_CONSULTA, "Consulta"),
    ]

    ESTADO_ACTIVO = "A"
    ESTADO_INACTIVO = "I"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    id_usuario = models.AutoField(db_column="idUsuario", primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    usuario = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=150, unique=True)
    dni = models.CharField(max_length=15, unique=True)
    rol = models.CharField(max_length=1, choices=ROL_CHOICES, default=ROL_OPERARIO)
    estado = models.CharField(max_length=1, choices=ESTADO_CHOICES, default=ESTADO_ACTIVO)

    # Necesario para el panel /admin/. No se otorga por ser Administrador:
    # el acceso al admin es una decisión aparte del rol dentro del sistema.
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "usuario"  # con qué campo se inicia sesión
    REQUIRED_FIELDS = ["email", "nombre", "apellido", "dni"]  # los pide createsuperuser

    class Meta:
        db_table = "Usuarios"
        ordering = ["apellido", "nombre"]
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def es_administrador(self):
        return self.rol == self.ROL_ADMINISTRADOR

    @property
    def is_active(self):
        """
        Django consulta `is_active` para permitir o bloquear el login.
        Se deriva de `estado` para no tener dos campos que signifiquen lo mismo:
        un usuario dado de baja no puede iniciar sesión.
        """
        return self.estado == self.ESTADO_ACTIVO

    def __str__(self):
        return f"{self.nombre_completo} ({self.usuario})"
