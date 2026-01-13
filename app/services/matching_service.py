"""
Matching Service - Core business logic for buyer-app matching
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import asyncpg
from app.matching.algorithm import run_match
from app.prompts.buyer_parser_prompts import SYSTEM_PROMPT, format_user_prompt, LABEL_CATALOG


class MatchingService:
    """Service for matching buyer requirements with applications"""
    
    def __init__(self, database_url: str, openai_api_key: str):
        self.database_url = database_url
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
    
    async def retry_openai_call(self, func, *args, retries=2, **kwargs):
        """Retry OpenAI API calls with exponential backoff"""
        for attempt in range(retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == retries:
                    raise Exception(f"OpenAI call failed after {retries} retries: {str(e)}")
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    async def parse_buyer_requirements(self, buyer_prompt: str) -> Dict[str, Any]:
        """
        Parse natural language buyer requirements into structured format using OpenAI.
        
        Args:
            buyer_prompt: Natural language text from buyer
        
        Returns:
            Structured buyer requirements dict
        
        Raises:
            Exception: If parsing fails after retries
        """
        user_prompt = format_user_prompt(buyer_prompt, LABEL_CATALOG)
        
        try:
            response = await self.retry_openai_call(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            buyer_struct = json.loads(response.choices[0].message.content)
            
            # Validate and provide fallback for missing fields
            buyer_struct.setdefault("buyer_text", buyer_prompt)
            buyer_struct.setdefault("labels_must", [])
            buyer_struct.setdefault("labels_nice", [])
            buyer_struct.setdefault("integration_required", [])
            buyer_struct.setdefault("integration_nice", [])
            buyer_struct.setdefault("constraints", {"price_max": None})
            buyer_struct.setdefault("notes", "")
            
            return buyer_struct
            
        except json.JSONDecodeError as e:
            # Fallback: return minimal structure
            return {
                "buyer_text": buyer_prompt,
                "labels_must": [],
                "labels_nice": [],
                "integration_required": [],
                "integration_nice": [],
                "constraints": {"price_max": None},
                "notes": f"Parser failed: {str(e)}"
            }
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (1536 floats)
        """
        response = await self.retry_openai_call(
            self.openai_client.embeddings.create,
            model="text-embedding-3-small",
            input=text[:8000]
        )
        
        return response.data[0].embedding
    
    async def get_app_names(self, conn: asyncpg.Connection, app_ids: List[str]) -> Dict[str, str]:
        """
        Batch fetch application names.
        
        Args:
            conn: Database connection
            app_ids: List of application UUIDs
        
        Returns:
            Dict mapping app_id -> app_name
        """
        if not app_ids:
            return {}
        
        query = """
            SELECT id, name
            FROM application
            WHERE id = ANY($1::uuid[])
        """
        
        rows = await conn.fetch(query, app_ids)
        
        return {str(row["id"]): row["name"] for row in rows}
    
    async def match_buyer_to_apps(
        self,
        buyer_prompt: str,
        top_k: int = 30,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Complete matching pipeline: parse requirements, generate embedding, and find matches.
        
        Args:
            buyer_prompt: Natural language buyer requirements
            top_k: Number of candidates to consider (vector search)
            top_n: Number of results to return
        
        Returns:
            Dict with buyer_struct and results list
        """
        # Step 1: Parse buyer requirements
        buyer_struct = await self.parse_buyer_requirements(buyer_prompt)
        
        # Step 2: Generate embedding for buyer text
        buyer_embedding = await self.generate_embedding(buyer_struct["buyer_text"])
        
        # Step 3: Connect to database and run matching algorithm
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # Run matching algorithm
            matches = await run_match(
                conn,
                buyer_struct,
                buyer_embedding,
                top_k=top_k,
                top_n=top_n
            )
            
            # Step 4: Fetch application names
            app_ids = [match["app_id"] for match in matches]
            app_names = await self.get_app_names(conn, app_ids)
            
            # Step 5: Enrich results with names
            results = [
                {
                    "app_id": match["app_id"],
                    "name": app_names.get(match["app_id"], "Unknown"),
                    "similarity_percent": match["similarity_percent"]
                }
                for match in matches
            ]
            
            return {
                "buyer_struct": buyer_struct,
                "results": results
            }
            
        finally:
            await conn.close()
