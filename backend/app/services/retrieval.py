
import asyncio
import httpx
from trafilatura import fetch_url, extract
from fastapi import HTTPException
import json
from typing import List, Dict, Optional

# A simple cache for search results to avoid repeated searches for the same query during a session
search_cache = {}

async def generate_search_queries(user_prompt: str, llm_assistant_model: str = "gemini-1.5-flash-latest") -> List[str]:
    """
    Uses a fast LLM to analyze a user prompt and generate a list of 3-5 diverse,
    keyword-focused search queries.
    """
    # This is a placeholder. In a real implementation, this would use an LLM
    # to generate more sophisticated queries.
    # For now, we'll just use the user's prompt as a single query.
    print(f"Generated search query for: {user_prompt}")
    return [user_prompt]

async def search_with_searxng(queries: List[str]) -> List[Dict]:
    """
    Performs a search for each query using a public SearxNG instance
    and returns a list of unique search result dictionaries.
    """
    unique_urls = set()
    all_results = []
    
    async with httpx.AsyncClient() as client:
        tasks = [client.get(f"https://searx.be/search?q={q}&format=json") for q in queries]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for response in responses:
        if isinstance(response, httpx.Response) and response.status_code == 200:
            try:
                data = response.json()
                for result in data.get("results", []):
                    if result.get("url") and result["url"] not in unique_urls:
                        unique_urls.add(result["url"])
                        all_results.append({
                            "url": result["url"],
                            "title": result.get("title"),
                            "content": result.get("content")
                        })
            except json.JSONDecodeError:
                continue # Ignore malformed JSON
    
    return all_results

async def extract_content_from_urls(urls: List[str]) -> str:
    """
    Fetches content from a list of URLs and extracts the main text content
    using Trafilatura.
    """
    all_text = []
    
    # Download in parallel
    documents = [fetch_url(url) for url in urls]
    
    for doc in documents:
        if doc:
            # Extract text and add a separator
            text = extract(doc, include_comments=False, include_tables=False)
            if text:
                all_text.append(text)

    return "\n\n---\n\n".join(all_text)

async def get_retrieved_context(user_prompt: str) -> Optional[str]:
    """
    Orchestrates the RAG pipeline: generates queries, searches, and extracts content.
    Returns a formatted string of the retrieved context or None if it fails.
    """
    try:
        # Step 1: Generate search queries
        search_queries = await generate_search_queries(user_prompt)

        # Step 2: Search with SearxNG
        search_results = await search_with_searxng(search_queries)
        
        # Limit to top 5 results to keep context concise
        top_5_urls = [result["url"] for result in search_results[:5]]

        if not top_5_urls:
            return None

        # Step 3: Extract content from URLs
        extracted_content = await extract_content_from_urls(top_5_urls)

        if not extracted_content:
            return None
        
        # Step 4: Format the final context
        formatted_context = f"Retrieved {len(top_5_urls)} documents for context.\n\n"
        formatted_context += extracted_content
        
        return formatted_context
        
    except Exception as e:
        print(f"Error in RAG pipeline: {e}")
        # In a real app, you'd want more robust logging here
        return None

