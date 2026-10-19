from fastapi import APIRouter, HTTPException, Query
import requests
from typing import Optional, List

router = APIRouter()


@router.get("/search")
def search_papers(
    query: str = Query(..., description="Research topic or keywords"),
    year_filter: Optional[int] = Query(None, description="Filter by publication year"),
    open_access_only: bool = Query(False, description="Only show open-access papers"),
    sort_by: str = Query("relevance", description="Sort by: relevance, year, citations"),
    per_page: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Search for academic papers using OpenAlex API.
    Supports filtering by year, open-access status, and sorting.
    """
    query = query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Please enter a research topic.")

    try:
        # Build OpenAlex API parameters
        params = {
            "search": query,
            "per-page": per_page,
        }
        
        # Add filters
        filters = []
        if year_filter:
            filters.append(f"publication_year:{year_filter}")
        if open_access_only:
            filters.append("is_oa:true")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        # Add sorting
        if sort_by == "year":
            params["sort"] = "publication_year:desc"
        elif sort_by == "citations":
            params["sort"] = "cited_by_count:desc"
        # relevance is default for OpenAlex
        
        response = requests.get(
            "https://api.openalex.org/works",
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        papers = []
        seen_dois = set()  # For deduplication
        
        for work in data.get("results", []):
            # Deduplicate by DOI
            doi = work.get("doi")
            if doi and doi in seen_dois:
                continue
            if doi:
                seen_dois.add(doi)
            
            # Extract authors
            authors = [
                authorship.get("author", {}).get("display_name")
                for authorship in work.get("authorships", [])
                if authorship.get("author", {}).get("display_name")
            ]

            # Extract abstract if available
            abstract = None
            if work.get("abstract_inverted_index"):
                # Reconstruct abstract from inverted index
                inverted_index = work["abstract_inverted_index"]
                word_positions = {}
                for word, positions in inverted_index.items():
                    for pos in positions:
                        word_positions[pos] = word
                
                if word_positions:
                    sorted_positions = sorted(word_positions.keys())
                    abstract = " ".join([word_positions[pos] for pos in sorted_positions])

            primary_location = work.get("primary_location") or {}
            source = primary_location.get("source") or {}
            
            # Get best available URL
            best_url = work.get("id")  # OpenAlex URL
            if primary_location.get("pdf_url"):
                best_url = primary_location["pdf_url"]
            elif primary_location.get("landing_page_url"):
                best_url = primary_location["landing_page_url"]

            papers.append(
                {
                    "title": work.get("display_name") or "Untitled",
                    "authors": authors,
                    "year": work.get("publication_year"),
                    "abstract": abstract,
                    "citations": work.get("cited_by_count", 0),
                    "doi": doi,
                    "url": best_url,
                    "openalex_url": work.get("id"),
                    "source": source.get("display_name"),
                    "is_open_access": work.get("open_access", {}).get("is_oa", False),
                }
            )

        return {
            "status": "success",
            "query": query,
            "total_results": len(papers),
            "papers": papers,
        }

    except requests.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Search request timed out. Please try again."
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Research paper search failed: {str(error)}",
        ) from error
