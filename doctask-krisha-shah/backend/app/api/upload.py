import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models import Document, Pile
from app.db.session import get_db
from app.schemas import DocumentOut
from app.storage.local_fs import LocalFileStorage

router = APIRouter(prefix="/piles", tags=["documents"])

ALLOWED_DOC_TYPES = {"contract", "amendment", "invoice", "other"}


@router.post("/{pile_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    pile_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    db: Session = Depends(get_db),
) -> Document:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=422, detail=f"doc_type must be one of {sorted(ALLOWED_DOC_TYPES)}")

    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    existing = (
        db.query(Document)
        .filter(Document.pile_id == pile_id, Document.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        existing.deduplicated = True  # informational only, not a DB column
        return existing

    ext = ""
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1]

    storage = LocalFileStorage(pile_id=str(pile_id))
    storage_path = storage.save(content, ext=ext)

    document = Document(
        pile_id=pile_id,
        doc_type=doc_type,
        storage_path=storage_path,
        content_hash=content_hash,
        original_filename=file.filename,
        mime_type=file.content_type,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document.deduplicated = False
    return document


@router.get("/{pile_id}/documents", response_model=list[DocumentOut])
def list_documents(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Document]:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    documents = db.query(Document).filter(Document.pile_id == pile_id).order_by(Document.ingested_at.desc()).all()
    for document in documents:
        document.deduplicated = False
    return documents
