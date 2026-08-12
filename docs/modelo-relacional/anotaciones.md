1\) El modelo NO contempla ninguna constraint específica para las tablas (UNIQUE, CHECK, DEFAULT, etc.), pues por ahora solo buscamos armar el diagrama relacional.



2\) Tabla Usuarios: el campo contrasenia es VARCHAR(255) ya que así se usa para cubrir cualquier algoritmo de hash (encriptación) en el futuro.



2\) Tabla Galpones: campo "descripcion" puede ser NULL. estado: operativo y no operativo.



3\) Tabla Lotes:

* fechaVaciado es un antributo que indica la fecha en que se hizo el vaciado sanitario de ese Lote y puede ser NULL ya que esa acción no se produce al crearse el lote.
* cantidadInicial es la cantidad de gallinas que conforman al lote inicialmente. cantidadActual se va actualizando a medida que ocurre algún descarte o cuando se hace el vaciado sanitario se vuelve 0.
* observaciones puede ser NULL, permitiendo cargar o no observaciones del lote.
* idGalpón está puesto como FK pero no es PK de la tabla Lotes, pues un lote puede no tener asignado un galpón inicialmente (por ejemplo cuando se lo compra) o puede cambiarse a otro galpón para, por ejemplo, un mantenimiento del galpón de donde se sacó el lote ese.
* estado: activo o baja.



4\) Tabla PlanesTransicion: fechaFin determinará cuándo el lote pasa a estado productivo. estado puede ser En Curso (C) y F (finalizado).



5\) Tabla Recolecciones:

* fecha es del tipo TIMESTAMP en MySQL, pero la idea es usar TIMESTAMP sin zona horaria en PostgreSQL. De esta forma, se registra la fecha y hora de las recolecciones que se cargan.
* observaciones puede ser NULL.



6\) Tabla TiposAlerta: contiene los tipos de alertas que pueden existir, por ejemplo

idTipoAlerta: 1      nombre: baja postura

No es necesario un estado, ya que son alertas que definimos nosotros como diseñadores del sistema.



7\) Tabla Alertas:

* descripcion es NOT NULL ya que explica la alerta. Toma el tipo de alerta y el lote, entonces en base a esto forma la alerta. Por ejemplo:

idAlerta: 1   idLote: 5 (que está actualmente en el galpón 3)   idTipoAlerta: 1 (nombre: postura baja)

\---> se forma la descripcion: "Postura baja del lote 5 en el galpón 3".

&#x20;

* estado puede ser 'P' (Pendiente) o 'R' (Resuelta). En caso de pasar a Resuelta, ya no se mostrará en el dashboard
* fechaGeneracion indica la fecha y hora en que se generó la alerta. Esto para que se pueda mostrar en la tabla de alertas en el sistema algo como "Generada hace 2 horas" o "Generada el 11/08/2026 a las 17:54 hs"



Propuesta: que las alertas sean solamente productivas (postura, descartes, etc.) y también de insumos (stock de materias primas).



8\) Tabla Salidas: estado puede ser 'P' (Pendiente, una vez que se crea) o 'F' (Finalizada, una vez que se concreta la salida).



9\) Tabla Descartes: cantidad es decimal porque puede ser un descarte en kg de alguna materia prima (no solo gallinas muertas).



10\) Tabla MateriasPrimas: stockMinimo permitirá generar una alerta por stock bajo de una materia prima en particular.



11\) Tabla Entradas: tipo: Gallinas (G) o Materias Primas (M).



12\) Tabla LineasEntrada: tiene una relación débil y puede ser null la FK con Lotes y con MateriasPrimas. Esto es porque puede tratarse de una entrada únicamente de Lote a un galpón, o puede tratarse de una entrada de únicamente materias primas. ANALIZAR ESTO BIEN. conclusión: se agrega un campo "tipo" en entradas para obligar a que idMateriaPrima o idLote no sea null al momento de cargar la entrada.



13\) Tabla LineasCompra: la cantidad es DECIMAL(10,2) ya que puede tratarse de una compra en kg, por ej. IDEM LINEASENTRADA CON EL TEMA DE LAS RELACIONES CON LOTES Y MATERIASPRIMAS.

