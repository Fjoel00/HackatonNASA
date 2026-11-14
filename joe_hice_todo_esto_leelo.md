# Joe, hice todo esto: leelo

## ¿Qué hace este proyecto?

La aplicación muestra focos de calor detectados por satélites. Puede usar datos de demostración o consultar datos reales de NASA FIRMS. En la página vas a encontrar un calendario, un mapa y herramientas de simulación.

## Cómo abrir la aplicación

1. Abrí una consola dentro de la carpeta del proyecto, `HackatonNASA`.
2. Escribí:

   ```bash
   docker compose up --build
   ```

3. Esperá a que termine de preparar los datos y abrí en el navegador:

   **http://localhost:8080**

La primera vez puede tardar un poco porque Docker prepara la aplicación. Después, cuando aparezca el mensaje de que está disponible, ya podés usarla.

Para cerrar, volvé a la consola y presioná **Ctrl+C**. También podés usar `docker compose down`.

## Cómo elegir los datos

En la barra de arriba de la página hay un selector con dos opciones:

- **Demo sintética:** datos inventados para probar la aplicación. Es la opción inicial y funciona sin consultar NASA FIRMS.
- **NASA FIRMS real:** datos consultados al servicio de NASA. Elegila y presioná **Aplicar**. La página muestra el progreso y se actualiza cuando termina.

La clave para NASA FIRMS ya está guardada en el archivo local `.env`. Por eso no hace falta escribirla al iniciar Docker ni copiarla en la página. Ese archivo está excluido del repositorio y de la imagen de Docker.

## Qué se agregó

- **Dockerfile:** prepara un entorno con todo lo que necesita el proyecto.
- **docker-compose.yml:** permite iniciar la aplicación con el comando `docker compose up --build` y abrirla en `localhost:8080`.
- **docker-entrypoint.sh:** prepara los datos iniciales y luego inicia la página.
- **app_server.py:** sirve la página y permite que el selector le pida al programa generar datos nuevos.
- **Selector de datos en la página:** permite cambiar entre la demo y NASA FIRMS, ver el avance y recibir un mensaje si hay un error.
- **.env:** guarda la clave de NASA FIRMS en esta computadora para que Docker la encuentre automáticamente.
- **.env.example:** muestra qué configuración se necesita si se prepara el proyecto en otra computadora.
- **.gitignore y .dockerignore:** evitan incluir la clave privada en el repositorio o dentro de la imagen.
- **README.md:** ahora explica cómo iniciar y usar la aplicación.

También se quitó la clave del código del programa para que no quede escrita ahí. Se comprobó que Docker arma la aplicación y que la consulta real a NASA FIRMS funciona.

## Cosas a tener en cuenta

- Para usar mapas, clima y rutas, la computadora necesita conexión a Internet.
- La demo usa datos inventados para pruebas; no representa incendios reales.
- Si cambiás el código o la configuración de Docker, iniciá con `docker compose up --build` para que Docker prepare los cambios.
