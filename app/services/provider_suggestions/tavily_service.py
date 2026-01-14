"""
Tavily Search Service for Provider Suggestions
Real web search powered by Tavily API
"""
from typing import Dict, List, Optional
from urllib.parse import urlparse


async def search_with_tavily(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search using Tavily API
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List of search results with title, url, snippet
    """
    try:
        from tavily import TavilyClient
        from app.core.config import settings
        
        api_key = settings.tavily_api_key
        if not api_key:
            raise ValueError("TAVILY_API_KEY not configured in settings")
        
        client = TavilyClient(api_key=api_key)
        
        print(f"🔍 Searching Tavily for: '{query}'")
        
        # Perform search
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"  # or "advanced" for deeper search
        )
        
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0)
            })
        
        print(f"   ✅ Found {len(results)} results")
        return results
        
    except ImportError:
        print("❌ Tavily library not installed. Run: pip install tavily-python")
        return []
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return []
    except Exception as e:
        print(f"❌ Search error: {str(e)}")
        return []


def generate_search_queries(card_title: str, card_description: str) -> List[str]:
    """Generate 3 optimized search queries"""
    combined = f"{card_title} {card_description}".lower()
    words = combined.split()
    
    # Extract important keywords
    important_words = [w for w in words if len(w) > 4 and w not in [
        'develop', 'create', 'application', 'system', 'feature',
        'designed', 'allows', 'users', 'should', 'would', 'could',
        'mobile', 'management'
    ]][:5]
    
    queries = []
    
    # Query 1: Keywords + "software provider"
    if important_words:
        queries.append(f"{' '.join(important_words[:3])} software provider")
    
    # Query 2: Keywords + "SaaS platform"
    if important_words:
        queries.append(f"{' '.join(important_words[:2])} SaaS platform")
    
    # Query 3: Title + "API service"
    queries.append(f"{card_title[:50]} API service")
    
    return queries[:3]


def rank_results(card_title: str, card_description: str, results: List[Dict]) -> Optional[Dict]:
    """Rank search results by relevance"""
    if not results:
        return None
    
    # Extract keywords
    keywords = set(card_title.lower().split() + card_description.lower().split())
    keywords = {w for w in keywords if len(w) > 3}
    
    scored_results = []
    for result in results:
        score = result.get("score", 0) * 100  # Tavily's native score
        
        # Keyword matching bonus
        title_words = set(result['title'].lower().split())
        snippet_words = set(result['snippet'].lower().split())
        
        title_matches = len(keywords & title_words)
        snippet_matches = len(keywords & snippet_words)
        
        score += title_matches * 10 + snippet_matches * 5
        
        # Quality indicators
        url = result['url'].lower()
        if any(x in url for x in ['.com', '.io', '.co']):
            score += 5
        if 'marketplace' in url or 'marketplace' in result['title'].lower():
            score += 10
        
        scored_results.append((score, result))
    
    # Sort by score
    scored_results.sort(reverse=True, key=lambda x: x[0])
    
    best = scored_results[0][1]
    
    # Extract company name
    company_name = best['title'].split('-')[0].split('|')[0].strip()
    if not company_name or len(company_name) < 2:
        domain = urlparse(best['url']).netloc
        company_name = domain.replace('www.', '').split('.')[0].title()
    
    # Determine marketplace URL
    marketplace_url = None
    if 'marketplace' in best['url'].lower():
        marketplace_url = best['url']
    
    return {
        "company_name": company_name,
        "company_url": best['url'],
        "marketplace_url": marketplace_url,
        "reasoning_brief": f"Top search result with relevance score. {best['snippet'][:100]}"
    }


async def suggest_provider_with_tavily(
    card_title: str,
    card_description: str
) -> Dict:
    """
    Suggest provider using Tavily web search
    
    Args:
        card_title: Card title
        card_description: Card description
        
    Returns:
        Dict with company_name, company_url, marketplace_url, reasoning_brief
    """
    print(f"\n🌐 Searching web for provider: '{card_title[:50]}...'")
    
    # Generate queries
    queries = generate_search_queries(card_title, card_description)
    print(f"📋 Generated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    
    # Search with first query (Tavily is more accurate with fewer queries)
    all_results = []
    for query in queries[:2]:  # Use only first 2 to save API calls
        results = await search_with_tavily(query, max_results=5)
        all_results.extend(results)
        if results:
            break  # If we got results, stop searching
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r['url'] not in seen_urls:
            seen_urls.add(r['url'])
            unique_results.append(r)
    
    print(f"\n✅ Total unique results: {len(unique_results)}")
    
    # Rank and select best
    best_match = rank_results(card_title, card_description, unique_results)
    
    if best_match:
        print(f"   🎯 Selected: {best_match['company_name']}")
        # Truncate reasoning to 60 words
        words = best_match['reasoning_brief'].split()
        if len(words) > 60:
            best_match['reasoning_brief'] = ' '.join(words[:60]) + '...'
        return best_match
    
    # Fallback if no results
    print("   ⚠️  No results found")
    return {
        "company_name": "No specific provider found",
        "company_url": "https://aws.amazon.com/marketplace",
        "marketplace_url": "https://aws.amazon.com/marketplace",
        "reasoning_brief": "No specific providers found in web search. Try AWS Marketplace for general software solutions."
    }
