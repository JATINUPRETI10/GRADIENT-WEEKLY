from fastapi import FastAPI
from pydantic import BaseModel
from duckduckgo_search import DDGS

app = FastAPI(title="MCP Web Search Server")

# ----- MCP Tool Schema -----

class WebSearchArgs(BaseModel):
    query: str
    max_results: int = 5


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


# ----- MCP Tool Implementation -----

@app.post("/tools/web_search")
async def web_search(args: WebSearchArgs):
    results = []

    with DDGS() as ddgs:
        search_results = ddgs.text(
            args.query,
            max_results=args.max_results
        )

        for r in search_results:
            results.append({
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body")
            })

    return {
        "content": results
    }


# ----- MCP Metadata Endpoints -----

@app.get("/.well-known/mcp.json")
def mcp_metadata():
    return {
        "name": "web-search-mcp",
        "version": "1.0.0",
        "tools": [
            {
                "name": "web_search",
                "description": "Search the web using DuckDuckGo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"}
                    },
                    "required": ["query"]
                }
            }
        ]
    }
