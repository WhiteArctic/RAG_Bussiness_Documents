"""Pipeline RAG construido a mano con el SDK google-genai.

Este módulo implementa, paso a paso, el flujo completo de Retrieval-Augmented
Generation. Se construye de forma incremental a lo largo del Bloque 3:

    [1] ingesta       (hecho)
    [2] chunking      (hecho)
    [3] embeddings    (hecho, en app/llm.py)
    [4] vector store (en memoria, numpy)    (hecho)
    [5] retrieval top-k (similitud coseno)  (hecho)
    [6] CONSTRUCCIÓN DE CONTEXTO            <-- este paso
    [7] GENERACIÓN CON CITAS                <-- este paso
    [8] integración en el endpoint /ask    (hecho) -> BLOQUE 3 COMPLETO

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


# ---------------------------------------------------------------------------
# [4] VECTOR STORE (en memoria) + [5] RETRIEVAL (similitud coseno, top-k)
# ---------------------------------------------------------------------------
import numpy as np

from app.llm import embed_texts, embed_query, generate_grounded_answer
from app.costs import estimate_cost_usd
from app.config import settings

# Cuántos chunks recupera el retrieval por pregunta. top_k=3: suficiente
# contexto sin inflar el prompt (costo/ruido). Trade-off ajustable.
TOP_K = 3


@dataclass
class RetrievedChunk:
    """Un chunk recuperado junto con su score de similitud (para citar/ordenar)."""

    source: str
    text: str
    score: float


class VectorStore:
    """Índice de vectores en memoria (numpy).

    Es la versión PoC de un vector store. En producción esto se reemplaza por
    un servicio gestionado (Vertex AI Vector Search, Pinecone, pgvector...),
    porque un índice en memoria no persiste ni se comparte entre instancias
    stateless de Cloud Run. La INTERFAZ (build / search) se mantendría igual:
    así cambiar el backend no toca el resto del pipeline.
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []
        self._matrix: np.ndarray | None = None  # shape (n_chunks, dim)

    def build(self, chunks: list[Chunk]) -> None:
        """Embebe los chunks UNA sola vez y los guarda como una matriz.

        Esto es la 'indexación' (offline): la operación cara se hace al
        arrancar, no por request.
        """
        if not chunks:
            raise ValueError("No hay chunks para indexar.")
        self._chunks = chunks
        vectors = embed_texts([c.text for c in chunks])
        # Normalizamos cada vector a norma 1. Así la similitud coseno se reduce
        # a un simple producto punto (más rápido) y es numéricamente estable.
        matrix = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self._matrix = matrix / np.clip(norms, 1e-12, None)

    def search(self, query: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        """Devuelve los top_k chunks más similares a la pregunta.

        Pasos: embeber la pregunta -> normalizar -> producto punto con toda la
        matriz (coseno) -> ordenar -> tomar los k mejores.
        """
        if self._matrix is None:
            raise RuntimeError("El índice no está construido. Llama a build() primero.")

        q = np.array(embed_query(query), dtype=np.float32)
        q = q / np.clip(np.linalg.norm(q), 1e-12, None)

        # Una sola multiplicación matriz-vector calcula TODAS las similitudes.
        # Vectorizado con numpy: rápido incluso con miles de chunks.
        scores = self._matrix @ q  # shape (n_chunks,)

        # argsort descendente y tomamos los primeros top_k.
        top_idx = np.argsort(-scores)[:top_k]
        return [
            RetrievedChunk(
                source=self._chunks[i].source,
                text=self._chunks[i].text,
                score=float(scores[i]),
            )
            for i in top_idx
        ]


def build_index(data_dir: Path = DATA_DIR) -> VectorStore:
    """Pipeline de indexación completo: cargar -> trocear -> embeber -> indexar.

    Se llama UNA vez al arrancar la app (ver Paso 8).
    """
    documents = load_documents(data_dir)
    chunks = chunk_documents(documents)
    store = VectorStore()
    store.build(chunks)
    return store


# ---------------------------------------------------------------------------
# [6] CONSTRUCCIÓN DE CONTEXTO + [7] GENERACIÓN CON CITAS
# ---------------------------------------------------------------------------


@dataclass
class RAGAnswer:
    """Respuesta final del pipeline RAG: texto + fuentes + métricas LLMOps."""

    answer: str
    sources: list[str]       # fuentes únicas usadas, para trazabilidad
    input_tokens: int = 0    # tokens de entrada (para costo)
    output_tokens: int = 0   # tokens de salida (para costo)
    cost_usd: float = 0.0    # costo estimado de la generación


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Formatea los chunks recuperados en un bloque de texto para el prompt.

    Decisiones:
    - Etiquetamos cada fragmento con su fuente ([Fuente: ...]). Así el LLM
      PUEDE citar, y el texto queda trazable dentro del propio prompt.
    - Numeramos los fragmentos: ayuda al modelo a referenciarlos y a nosotros
      a depurar qué contexto recibió.
    """
    bloques = []
    for i, c in enumerate(chunks, start=1):
        bloques.append(f"[Fragmento {i}] [Fuente: {c.source}]\n{c.text}")
    return "\n\n".join(bloques)


def answer_question(store: VectorStore, question: str, top_k: int = TOP_K) -> RAGAnswer:
    """Pipeline RAG de query completo (lo que ocurre en cada /ask):

        pregunta -> retrieval top-k -> armar contexto -> generar (grounded)

    Devuelve la respuesta y las fuentes únicas, en orden de relevancia.
    """
    retrieved = store.search(question, top_k=top_k)
    context = build_context(retrieved)
    result = generate_grounded_answer(question, context)

    # Fuentes únicas preservando el orden de relevancia (dict.fromkeys = dedup
    # estable). Útil para citar sin repetir el mismo archivo.
    sources = list(dict.fromkeys(c.source for c in retrieved))

    # Métricas LLMOps: tokens reales + costo estimado de esta request.
    cost = estimate_cost_usd(
        settings.gemini_model, result.input_tokens, result.output_tokens
    )
    return RAGAnswer(
        answer=result.text,
        sources=sources,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=cost,
    )
