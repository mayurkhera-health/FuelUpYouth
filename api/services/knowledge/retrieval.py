import boto3
from dataclasses import dataclass
from typing import List

@dataclass
class KnowledgeChunk:
    title: str
    content: str
    source: str
    heading: str = ""
    source_urls: list = None
    
import os
KNOWLEDGE_BASE_ID = os.environ.get("BEDROCK_KB_ID", "TY90NW9C05")
REGION = "us-east-1"

client = boto3.client("bedrock-agent-runtime", region_name=REGION)

def retrieve(question: str, top_n: int = 5) -> List[KnowledgeChunk]:
    try:
        response = client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": question},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": top_n}
            },
        )
        chunks = []
        for result in response.get("retrievalResults", []):
            content = result.get("content", {}).get("text", "")
            location = result.get("location", {})
            s3_uri = location.get("s3Location", {}).get("uri", "")
            chunks.append(KnowledgeChunk(
                title=s3_uri.split("/")[-1] if s3_uri else "Knowledge Base",
                content=content,
                source=s3_uri,
                source_urls=[s3_uri] if s3_uri else [],
            ))
        return chunks
    except Exception as e:
        print(f"KB retrieval error: {e}")
        return []
