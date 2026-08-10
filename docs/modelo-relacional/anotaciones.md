1\) El modelo NO contempla ninguna constraint específica (UNIQUE, CHECK, DEFAULT, etc.).



2\) Tabla Galpones: campo "descripcion" puede ser NULL.



3\) Tabla Lotes: 	

* fechaVaciado es un antributo que indica la fecha en que se hizo el vaciado sanitario de ese Lote y puede ser NULL ya que esa acción no se produce al crearse el lote.
* cantidadInicial es la cantidad de gallinas que conforman al lote inicialmente. cantidadActual se va actualizando a medida que ocurre algún descarte o cuando se hace el vaciado sanitario se vuelve 0.
* observaciones puede ser NULL, permitiendo cargar o no observaciones del lote.
* idGalpón está puesto como FK pero no es PK de la tabla Lotes.



4\) Tabla PlanesTransicion: fechaFin puede ser NULL, ya que este solo tendrá un valor cuando finalice el plan de transición.



5\) Tabla Recolecciones: 

* fecha y hora separados. hora es time without time zone (solo tiempo, sin zona horaria).
* observaciones puede ser NULL (opcional).

