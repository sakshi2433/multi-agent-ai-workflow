import asyncio
from app.graph.orchestrator import WorkflowOrchestrator

async def main():
    orchestrator = WorkflowOrchestrator()
    result = await orchestrator.execute_workflow(
        "test-workflow-001",
        "Search for the latest developments in artificial intelligence"
    )
    print(result)

asyncio.run(main())
