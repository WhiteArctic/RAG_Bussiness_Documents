"""Pipeline RAG construido a mano con el SDK google-genai.

Este módulo implementa, paso a paso, el flujo completo de Retrieval-Augmented
Generation. Se construye de forma incremental a lo largo del Bloque 3:

    [1] INGESTA  <-- este paso
    [2] chunking
    [3] embeddings
    [4] vector store (en memoria, numpy)
    [5] retrieval top-k (similitud coseno)
    [6] construcción de contexto
    [7] generación con citas
    [8] integración en el endpoint /ask

Decisión pedagógica: NO usamos LangChain ni LlamaIndex. Hacemos cada pieza a
mano para entender el mecanismo (y poder defenderlo en la entrevista).
"""

from dataclasses import dataclass
from pathlib import Path

# Carpeta donde viven los documentos crudos. Relativa a la raíz del proyecto.
# En producción esto vendría de configuración (GCS, S3, una DB...), no hardcodeado.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Document:
    """Un documento ingerido.

    No usamos un simple string: guardamos también 'source' (el nombre del
    archivo). Esa metadata es imprescindible para citar la fuente en la
    respuesta final (Paso 7). Si perdemos la fuente aquí, no hay forma de
    recuperarla después.
    """

    source: str  # nombre del archivo de origen, ej. "politica_reembolsos.txt"
    text: str    # contenido completo del documento


def load_documents(data_dir: Path = DATA_DIR) -> list[Document]:
    """Carga todos los archivos .txt de la carpeta de datos.

    Decisiones de diseño:
    - Solo .txt: texto plano. Parsear PDF/DOCX (layout, tablas, OCR) añade
      complejidad que no aporta al mecanismo RAG; es un 'siguiente paso'.
    - encoding='utf-8': fijamos el encoding explícitamente para no depender del
      sistema operativo (en Windows el default no es utf-8 y rompería acentos).
    - Fail-fast suave: ignoramos archivos vacíos para no meter ruido al índice,
      pero avisamos si la carpeta entera no existe o está vacía.
    """
    if not data_dir.exists():
        raise FileNotFoundError(
            f"La carpeta de datos no existe: {data_dir}. "
            "Crea 'data/' y coloca ahí los documentos .txt."
        )

    documents: list[Document] = []
    # sorted() -> orden determinista: útil para reproducibilidad y tests.
    for path in sorted(data_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue  # ignoramos archivos vacíos: no aportan al índice
        documents.append(Document(source=path.name, text=text))

    if not documents:
        raise ValueError(
            f"No se encontraron documentos .txt con contenido en {data_dir}."
        )

    return documents

# ---------------------------------------------------------------------------
# [2] CHUNKING
# ---------------------------------------------------------------------------
 
# Parámetros de chunking. Expuestos como constantes para poder ajustarlos y
# justificarlos. ~19% de overlap, dentro del rango recomendado (10-20%).
CHUNK_SIZE = 800      # caracteres por chunk (~1 sección/idea)
CHUNK_OVERLAP = 150   # caracteres repetidos entre chunks consecutivos
 
 
@dataclass
class Chunk:
    """Un trozo de un documento, listo para vectorizar.
 
    Arrastra 'source' desde el Document de origen: sin esto, al convertir el
    texto en un vector perderíamos de qué archivo vino (ver Paso 1). Lo
    necesitaremos para citar la fuente en la respuesta final.
    """
 
    source: str  # archivo de origen, heredado del Document
    text: str    # contenido del chunk
 
 
def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Parte un texto en trozos de 'size' caracteres con 'overlap' de solape.
 
    Mecanismo (ventana deslizante):
    - Tomamos [0:size], luego avanzamos 'size - overlap' y tomamos el siguiente.
    - El overlap hace que el final de un chunk se repita al inicio del siguiente,
      para no partir una idea justo en el corte.
 
    Guardas (defensa en la entrevista):
    - overlap debe ser < size, si no el puntero no avanzaría (bucle infinito).
    """
    if size <= 0:
        raise ValueError("size debe ser > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap debe estar en el rango [0, size)")
 
    text = text.strip()
    if not text:
        return []
 
    step = size - overlap  # cuánto avanza la ventana en cada iteración
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
 
 
def chunk_documents(documents: list[Document]) -> list[Chunk]:
    """Trocea una lista de Documents en Chunks, preservando el 'source'."""
    chunks: list[Chunk] = []
    for doc in documents:
        for piece in chunk_text(doc.text):
            chunks.append(Chunk(source=doc.source, text=piece))
    return chunks