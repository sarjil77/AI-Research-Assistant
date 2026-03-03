from schemas.agent_state import AgentState

# -------- Node 1: Research --------
async def internet_search(state: AgentState) -> AgentState:
    query = state["query"]

    # Get persistent manager from state
    mcp_manager = state.get("mcp_manager")
    print("Available tools:", state["mcp_manager"].all_tools.keys())

    if mcp_manager is None:
        raise RuntimeError("MCP Manager not found in state")

    results = await mcp_manager.mcp_search(
        query=query
    )

    state["response"] = results
    state.setdefault("research_agent", []).append(results)
    state["steps"] = state.get("steps", []) + ["internet_search"]

    return state