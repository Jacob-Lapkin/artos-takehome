"""VectorStoreService: Standard PDF chunking with LangChain.

Uses LangChain with Google Gemini embeddings and FAISS for vector storage.
Includes BM25 for hybrid retrieval.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List
import logging
import time

from app.config import Config
from app.utils.io_utils import ensure_dir, read_json
from app.utils.bm25 import build_bm25_model, save_bm25
from dotenv import load_dotenv

load_dotenv()

# Import required libraries
try:
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document
except ImportError as e:
    raise RuntimeError(f"Required dependencies not installed: {e}")


class VectorStoreService:
    """Build and manage per-index FAISS and BM25 stores."""

    def __init__(self, cfg: Config = Config):
        self.cfg = cfg
        # Target ~800 tokens per chunk (4 chars/token)
        self.target_chunk_size = 3200
        self.chunk_overlap = 400
        
    def _index_dir(self, index_id: str) -> str:
        return os.path.join(self.cfg.INDEXES_DIR, index_id)

    def _faiss_dir(self, index_id: str) -> str:
        return os.path.join(self._index_dir(index_id), "faiss")

    def _bm25_path(self, index_id: str) -> str:
        return os.path.join(self._index_dir(index_id), "bm25.json")

    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Standard LangChain chunking - simple and reliable.
        Creates chunks of ~800 tokens with overlap.
        """
        if not documents:
            logging.error("No documents provided for chunking")
            return []
            
        logging.info(f"Starting chunking for {len(documents)} documents")
        
        # Use RecursiveCharacterTextSplitter for intelligent splitting
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.target_chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
            keep_separator=True,
        )
        
        # Split all documents
        all_chunks = []
        for doc in documents:
            if not doc.page_content or not doc.page_content.strip():
                logging.warning(f"Skipping empty document on page {doc.metadata.get('page', 'unknown')}")
                continue
            
            # Split the document
            chunks = splitter.split_documents([doc])
            
            # Add chunk index to metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_index": i,
                    "original_page": doc.metadata.get("page", 1),
                    "source_file": doc.metadata.get("source", ""),
                })
            
            all_chunks.extend(chunks)
        
        # Filter out tiny chunks
        filtered_chunks = []
        for chunk in all_chunks:
            if len(chunk.page_content.strip()) >= 50:  # Minimum 50 chars
                filtered_chunks.append(chunk)
            else:
                logging.debug(f"Skipping tiny chunk: {len(chunk.page_content)} chars")
        
        logging.info(f"Chunking completed: {len(filtered_chunks)} total chunks")
        return filtered_chunks

    def build_from_pdf(self, file_path: str, file_id: str, index_id: str) -> Dict[str, Any]:
        """Process PDF → standard chunks → vector store."""
        logging.info(f"Processing PDF: {file_path}")
        
        # Load PDF pages
        loader = PyMuPDFLoader(file_path)
        documents = loader.load()
        logging.info(f"Loaded {len(documents)} pages")
        
        if not documents:
            raise RuntimeError("No pages loaded from PDF")
        
        # Standard chunking
        chunk_docs = self._chunk_documents(documents)
        logging.info(f"Created {len(chunk_docs)} chunks")
        
        if not chunk_docs:
            raise RuntimeError("No valid chunks created from PDF")
        
        # Convert to expected format
        chunks = []
        sections = []
        
        # Create a default section for all chunks
        sections.append({
            "section_path": "Document",
            "heading": "Document Content",
            "heading_norm": "document content",
            "page_start": 1,
            "page_end": len(documents),
            "body": "",
            "paras": []
        })
        
        # Convert chunks to expected format
        for i, chunk_doc in enumerate(chunk_docs):
            chunk_id = hashlib.sha1(
                f"{file_id}|{i}|{chunk_doc.page_content[:100]}".encode('utf-8')
            ).hexdigest()
            
            # Get page info from metadata
            page_num = chunk_doc.metadata.get("original_page", 1)
            
            chunks.append({
                "chunk_id": chunk_id,
                "file_id": file_id,
                "section_path": "Document",
                "heading_norm": "document content",
                "page_span": [page_num, page_num],
                "text": chunk_doc.page_content,
                "metadata": {
                    "source": file_path,
                    "page": page_num,
                    "chunk_index": i,
                    "token_count": len(chunk_doc.page_content) // 4
                }
            })
        
        # Log chunk statistics
        token_counts = [c["metadata"]["token_count"] for c in chunks]
        if token_counts:
            avg_tokens = sum(token_counts) / len(token_counts)
            min_tokens = min(token_counts)
            max_tokens = max(token_counts)
            logging.info(f"Chunk statistics: avg={avg_tokens:.0f}, min={min_tokens}, max={max_tokens} tokens")
        
        # Save and build vector store
        from app.services.state_service import write_index_artifacts
        
        initial_meta = {
            "index_id": index_id,
            "file_id": file_id,
            "store": "none",
            "embed_model": None,
            "n_chunks": len(chunks),
            "pages": len(documents),
            "created_at": int(time.time()),
            "stage": "parsed_segmented_chunked",
            "vector_stats": {},
        }
        
        write_index_artifacts(index_id, initial_meta, sections, chunks)
        
        return self._build_vector_store(index_id, chunks, sections)

    def _build_vector_store(self, index_id: str, chunks: List[Dict], sections: List[Dict]) -> Dict[str, Any]:
        """Build FAISS and BM25 indices from chunks."""
        logging.info(f"Building vector store for {len(chunks)} chunks")
        
        if not chunks:
            raise RuntimeError("No chunks provided for vector store creation")
        
        # Convert to LangChain documents
        docs = []
        for chunk in chunks:
            # Skip chunks with empty text
            if not chunk.get("text") or not chunk["text"].strip():
                logging.warning(f"Skipping chunk with empty text: {chunk.get('chunk_id')}")
                continue
                
            meta = {
                "chunk_id": chunk["chunk_id"],
                "file_id": chunk["file_id"],
                "section_path": chunk["section_path"],
                "heading_norm": chunk["heading_norm"],
                "page_span": chunk["page_span"],
            }
            docs.append(Document(page_content=chunk["text"], metadata=meta))
        
        if not docs:
            raise RuntimeError("No valid documents created from chunks")
        
        logging.info(f"Created {len(docs)} valid documents for embedding")
        
        # Create embeddings and FAISS index
        embeddings = GoogleGenerativeAIEmbeddings(model=self.cfg.EMBED_MODEL)
        
        # Safety check - test embeddings first
        try:
            test_embedding = embeddings.embed_query("test")
            logging.info(f"Embedding test successful, dimension: {len(test_embedding)}")
        except Exception as e:
            logging.error(f"Embedding test failed: {e}")
            raise RuntimeError(f"Google Gemini embeddings not working: {e}")
        
        vs = FAISS.from_documents(documents=docs, embedding=embeddings)
        
        # Save FAISS
        fdir = self._faiss_dir(index_id)
        ensure_dir(fdir)
        vs.save_local(folder_path=fdir, index_name="index")
        logging.info(f"Saved FAISS index to {fdir}")
        
        # Build and save BM25
        corpus = [f"{d.metadata['heading_norm']}\n{d.page_content}" for d in docs]
        bm25 = build_bm25_model(corpus)
        save_bm25(self._bm25_path(index_id), bm25)
        logging.info(f"Saved BM25 index")
        
        # Update metadata
        from app.services.state_service import write_index_artifacts
        
        final_meta = {
            "index_id": index_id,
            "file_id": chunks[0]["file_id"] if chunks else "unknown",
            "store": "faiss",
            "embed_model": self.cfg.EMBED_MODEL,
            "n_chunks": len(chunks),
            "pages": len(sections),
            "created_at": int(time.time()),
            "stage": "indexed",
            "vector_stats": {
                "n_chunks": len(chunks),
                "embed_model": self.cfg.EMBED_MODEL,
                "faiss_path": fdir,
                "bm25_path": self._bm25_path(index_id),
            },
        }
        
        write_index_artifacts(index_id, final_meta, sections, chunks)
        
        return final_meta["vector_stats"]

    def build_from_chunks(self, index_id: str) -> Dict[str, Any]:
        """Build vector store from existing chunks (backward compatibility)."""
        idir = self._index_dir(index_id)
        chunks = read_json(os.path.join(idir, "chunks.json"), default=[]) or []
        sections = read_json(os.path.join(idir, "sections.json"), default=[]) or []
        
        if not chunks:
            raise RuntimeError("No chunks found for index")
        
        logging.info(f"Loaded {len(chunks)} existing chunks")
        
        # Ensure required fields
        for chunk in chunks:
            if not chunk.get("chunk_id"):
                content = f"{chunk.get('file_id', 'unknown')}|{chunk.get('text', '')[:100]}"
                chunk["chunk_id"] = hashlib.sha1(content.encode('utf-8')).hexdigest()
        
        return self._build_vector_store(index_id, chunks, sections)