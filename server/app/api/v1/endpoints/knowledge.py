from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()


class DocumentMetadata(BaseModel):
    filename: str
    total_pages: int
    topics: List[str]
    status: str


@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(file: UploadFile = File(...)):
    """Upload a new document"""
    pass


@router.get("/documents", response_model=List[DocumentMetadata])
async def list_documents():
    """List all documents"""
    pass
