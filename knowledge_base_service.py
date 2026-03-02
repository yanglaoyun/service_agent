from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.knowledge_base import KnowledgeBase, KnowledgeBaseFile
from app.services.rag_service import RAGService
from app.core.logger import get_logger

logger = get_logger(service="knowledge_base_service")

class KnowledgeBaseService:
    @staticmethod
    async def create_knowledge_base(name: str, description: str = None, user_id: int = None) -> KnowledgeBase:
        async with AsyncSessionLocal() as session:
            try:
                kb = KnowledgeBase(name=name, description=description, user_id=user_id)
                session.add(kb)
                await session.commit()
                await session.refresh(kb)
                return kb
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating knowledge base: {e}")
                raise

    @staticmethod
    async def list_knowledge_bases(user_id: int = None) -> List[KnowledgeBase]:
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(KnowledgeBase).options(selectinload(KnowledgeBase.files))
                if user_id:
                    # List user's KBs and public ones (where user_id is None)
                    stmt = stmt.where((KnowledgeBase.user_id == user_id) | (KnowledgeBase.user_id == None))
                result = await session.execute(stmt)
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Error listing knowledge bases: {e}")
                raise

    @staticmethod
    async def get_knowledge_base(kb_id: int) -> Optional[KnowledgeBase]:
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(KnowledgeBase).options(selectinload(KnowledgeBase.files)).where(KnowledgeBase.id == kb_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Error getting knowledge base {kb_id}: {e}")
                raise

    @staticmethod
    async def delete_knowledge_base(kb_id: int):
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
                result = await session.execute(stmt)
                kb = result.scalar_one_or_none()
                if kb:
                    await session.delete(kb)
                    await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting knowledge base {kb_id}: {e}")
                raise

    @staticmethod
    async def add_file_to_knowledge_base(kb_id: int, file_info: dict) -> KnowledgeBaseFile:
        async with AsyncSessionLocal() as session:
            try:
                # First, verify KB exists
                kb = await session.get(KnowledgeBase, kb_id)
                if not kb:
                    raise ValueError(f"Knowledge Base {kb_id} not found")

                # Process file with RAG service to get index_id
                rag_service = RAGService()
                result = await rag_service.process_file(file_info)
                
                if result.get("status") == "error":
                    raise Exception(result.get("error"))

                index_id = result.get("index_id")
                
                # Create file record
                kb_file = KnowledgeBaseFile(
                    kb_id=kb_id,
                    filename=file_info["original_name"],
                    file_path=file_info["path"],
                    index_id=index_id
                )
                session.add(kb_file)
                await session.commit()
                await session.refresh(kb_file)
                return kb_file
            except Exception as e:
                await session.rollback()
                logger.error(f"Error adding file to knowledge base {kb_id}: {e}")
                raise
