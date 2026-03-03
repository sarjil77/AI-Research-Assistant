import logging
import os
import uuid
import warnings
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import uvicorn
from src.mcp_search_client import MCPManager
load_dotenv()

# ------------------- Warnings & Logging -------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore")
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)


PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("URL_SCHEMA", "0.0.0.0")

from utils.logger import create_logger
from src.workflow import run_workflow
from src.db import insert_log
from src.cache import get_cache, set_cache, generate_cache_key

logging_root = os.getenv("LOGGER_ROOT")
logger = create_logger(logging_root, "MAIN")

# ------------------- FastAPI App -------------------
app = FastAPI(title="AI Content Research Assistant")

mcp_manager = MCPManager()

@app.on_event("startup")
async def startup_event():
    await mcp_manager.startup()

# ------------------- Health Check -------------------
@app.get("/")
async def health_check():
    return {"status": "running", "app": "AI Content Research Assistant"}


# ------------------- Main Endpoint -------------------
@app.post("/query")
async def process_query(
    query: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """
    Receives user query + files → sends to workflow → returns output.
    """
    request_id = str(uuid.uuid4())
    try:
        if not query:
            raise HTTPException(status_code=400, detail="Invalid or missing query")

        # -------- Cache --------
        cache_key = generate_cache_key(query, files)
        cached = get_cache(cache_key)

        if cached:
            logger.info("Cache hit")
            return {
                "query": query,
                "result": cached
            }

        logger.info("Cache miss")
        logger.info(
            "Workflow has started for query: %s, Request ID: %s",
            query,
            request_id
        )

        # -------- Workflow --------
        result = await run_workflow(query, files,mcp_manager, logger)

        set_cache(cache_key, result)

        success = True if result else False

        # -------- DB Logging --------
        insert_log(query, result, success)

        return {
            "query": query,
            "result": result
        }

    except Exception as e:
        insert_log(query, str(e), False)

        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ------------------- Run Server -------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT)