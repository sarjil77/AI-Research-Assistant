from schemas.document import Document
from typing import TypedDict, List, Any
from typing_extensions import NotRequired

class AgentState(TypedDict):
    query: str
    documents: List[Document]
    research_agent: List[str]   
    decision: str
    steps: List[str]
    iteration: int
    response: str
    final_answer: str
    mcp_manager: NotRequired[Any]