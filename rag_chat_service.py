from typing import List, Dict, AsyncGenerator
from .embedding_service import EmbeddingService
from openai import AsyncOpenAI
from ..core.config import settings
import json
import re
from ..core.logger import get_logger

logger = get_logger(service="rag_chat")

class RAGChatService:
    def __init__(self):
        logger.info("Initializing RAG Chat Service")
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.embedding_service = EmbeddingService()
        
        # 添加结构化输出的提示模板
        self.structured_prompt = """

        基于以下文档内容回答用户的问题：

        {context}

        用户问题：{query}
        """

    async def generate_stream(self, messages: List[Dict], index_ids: List[str] = None) -> AsyncGenerator[str, None]:
        """基于文档生成回复"""
        try:
            logger.info(f"Processing chat request with index_ids: {index_ids}")
            # 获取用户最新的问题
            user_query = messages[-1]["content"]

            search_results = []
            # 如果提供了索引ID列表，进行文档检索
            if index_ids:
                if isinstance(index_ids, str):
                    index_ids = [index_ids]
                
                all_results = []
                for idx_id in index_ids:
                    try:
                        # 加载对应的索引
                        self.embedding_service._load_index(idx_id)
                        # 搜索相关内容
                        results = await self.embedding_service.search(user_query, top_k=3)
                        all_results.extend(results)
                    except Exception as e:
                        logger.error(f"Error searching index {idx_id}: {e}")
                
                # 对结果排序 (L2距离越小越相似)
                all_results.sort(key=lambda x: x['score'])
                # 取前5个
                search_results = all_results[:5]
                
                if search_results:
                    # 首先输出检索结果
                    retrieval_results = {
                        "type": "retrieval_results",
                        "total": len(search_results),
                        "results": [
                            {
                                "content": result["content"],
                                "score": result["score"],
                                "metadata": result["metadata"]
                            }
                            for result in search_results
                        ]
                    }
                    # 一次性输出检索结果
                    yield json.dumps(retrieval_results, ensure_ascii=False) + "\n\n"
                    
                    # 构建上下文
                    context = "\n\n".join([
                        f"相关段落 {i+1}:\n{result['content']}"
                        for i, result in enumerate(search_results)
                    ])
                    
                    # 使用结构化提示
                    prompt = self.structured_prompt.format(
                        context=context,
                        query=user_query
                    )
                    
                    # 使用新的消息上下文
                    rag_messages = [
                        {
                            "role": "system",
                            "content": "你是一个专业的文档问答助手。请使用结构化的方式组织回答，确保格式清晰。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                else:
                    # 返回空检索结果
                    yield json.dumps({
                        "type": "retrieval_results",
                        "total": 0,
                        "results": []
                    }, ensure_ascii=False) + "\n\n"
                    
                    yield "未找到相关的文档内容。将基于通用知识回答：\n\n"
                    rag_messages = messages
            else:
                 # No index provided
                 rag_messages = messages

            #model="deepseek-ai/DeepSeek-V3" huggingface namespace
            response =  await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=rag_messages,
                stream=True
            )

            async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        # 使用 ensure_ascii=False 来保持中文字符
                        content = json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
                        yield f"data: {content}\n\n"
   

        except Exception as e:
            logger.error(f"Error in generate_stream: {str(e)}", exc_info=True)
            raise