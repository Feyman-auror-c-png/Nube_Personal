/**
 * Script de demostración en la carpeta Proyectos
 * Puedes previsualizar y editar este código directamente desde la nube.
 */

const configuracionNube = {
  nombre: "Nimbus Personal Cloud",
  version: "1.0.0",
  formatosSoportados: ["md", "png", "jpg", "svg", "mp4", "mp3", "pdf", "csv", "js", "py", "json"],
  almacenamientoLocal: true,
};

function saludarUsuario(usuario = "Creador") {
  return `¡Hola, ${usuario}! Tu nube personal está funcionando al 100%.`;
}

console.log(saludarUsuario());
