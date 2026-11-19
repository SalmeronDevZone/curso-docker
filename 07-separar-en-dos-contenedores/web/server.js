// WEB de NOTAS: el "frontend".
//
// Este servidor NO guarda datos. Cada vez que alguien abre la página, le pide
// las notas a la API por HTTP. ¿Dónde está la API? Nos lo dice la variable de
// entorno API_URL. Esa variable es LA CLAVE para poder separar las dos
// aplicaciones en contenedores distintos:
//
//   - las dos apps en el mismo contenedor  -> API_URL=http://localhost:5000
//   - cada app en su propio contenedor     -> API_URL=http://api:5000
//                                              ("api" = nombre del contenedor)

const express = require("express");
const os = require("os");

const PORT = Number(process.env.PORT || 3000);
const API_URL = process.env.API_URL || "http://localhost:5000";
const CONTENEDOR = os.hostname(); // en Docker: el ID corto del contenedor

const app = express();
app.use(express.urlencoded({ extended: false }));

function escapar(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// fetch() de Node guarda la causa real del error en err.cause.code:
//   ENOTFOUND    -> el NOMBRE (p. ej. "api") no se resuelve: ¿están en la misma red?
//   ECONNREFUSED -> el nombre resuelve, pero nadie escucha en ese puerto
//   EAI_AGAIN    -> fallo temporal de DNS
function describirError(err) {
  const codigo = err.cause && err.cause.code;
  return codigo ? `${codigo} (${err.cause.message || err.message})` : err.message;
}

function pagina({ notas = [], contenedorApi = "?", error = null }) {
  const filas = notas.length
    ? notas
        .map((n) => `    <li><strong>#${n.id}</strong> ${escapar(n.texto)} <small>${escapar(n.creada)}</small></li>`)
        .join("\n")
    : "    <li><em>No hay notas todavía.</em></li>";

  return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Notas · Curso de Docker</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 680px; margin: 2rem auto; padding: 0 1rem; color: #1f2933; }
    h1 { margin-bottom: .25rem; }
    .info { background: #eef2f7; border-radius: 8px; padding: .75rem 1rem; font-size: .9rem; line-height: 1.6; }
    .error { background: #fde8e8; color: #9b1c1c; border-radius: 8px; padding: .75rem 1rem; }
    form { display: flex; gap: .5rem; margin: 1.5rem 0; }
    input { flex: 1; padding: .5rem; font-size: 1rem; }
    button { padding: .5rem 1rem; font-size: 1rem; cursor: pointer; }
    li { margin: .4rem 0; }
    small { color: #616e7c; }
    code { background: #dde3ea; padding: 0 .3rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>📝 Notas</h1>
  <p>Mini-aplicación para aprender Docker.</p>
  <div class="info">
    Página servida por <strong>WEB</strong> desde el contenedor <code>${escapar(CONTENEDOR)}</code><br>
    Datos servidos por la <strong>API</strong> desde el contenedor <code>${escapar(contenedorApi)}</code><br>
    <small>API_URL = <code>${escapar(API_URL)}</code></small>
  </div>
  ${error ? `<p class="error">⚠️ ${escapar(error)}</p>` : ""}
  <form method="post" action="/notas">
    <input name="texto" placeholder="Escribe una nota..." required autofocus>
    <button type="submit">Guardar</button>
  </form>
  <ul>
${filas}
  </ul>
</body>
</html>`;
}

app.get("/", async (req, res) => {
  try {
    const respuesta = await fetch(`${API_URL}/api/notas`);
    if (!respuesta.ok) throw new Error(`la API respondió con estado ${respuesta.status}`);
    const datos = await respuesta.json();
    res.send(pagina({ notas: datos.notas, contenedorApi: datos.contenedor }));
  } catch (err) {
    const detalle = describirError(err);
    console.error(`[web] No puedo hablar con la API en ${API_URL}: ${detalle}`);
    res.status(502).send(pagina({ error: `No puedo conectar con la API en ${API_URL} → ${detalle}` }));
  }
});

app.post("/notas", async (req, res) => {
  try {
    const respuesta = await fetch(`${API_URL}/api/notas`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: req.body.texto }),
    });
    if (!respuesta.ok) throw new Error(`la API respondió con estado ${respuesta.status}`);
  } catch (err) {
    console.error(`[web] Error guardando la nota: ${describirError(err)}`);
  }
  res.redirect("/");
});

app.get("/health", (req, res) => {
  res.json({ estado: "ok", servicio: "web", contenedor: CONTENEDOR });
});

const servidor = app.listen(PORT, "0.0.0.0", () => {
  console.log(`[web] Escuchando en el puerto ${PORT} (contenedor ${CONTENEDOR}). API_URL=${API_URL}`);
});

// "docker stop" envía SIGTERM (y Ctrl+C envía SIGINT). Node, cuando es el
// PID 1 del contenedor, NO los atiende por defecto: los capturamos para
// cerrar limpio en vez de esperar 10 s a que Docker lo mate con SIGKILL.
for (const senal of ["SIGTERM", "SIGINT"]) {
  process.on(senal, () => {
    console.log(`[web] ${senal} recibido: cerrando.`);
    servidor.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 2000).unref();
  });
}
