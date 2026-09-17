#!/usr/bin/env python3
"""Run the evaluation suite for the Multi-Agent AI Workflow system."""
import asyncio
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
from app.core.config import settings


class EvaluationSuite:
    """Evaluation suite for testing the multi-agent system."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.results: List[Dict[str, Any]] = []

    async def run_scenario(self, scenario_name: str, request: str,
                         expected_tools: List[str] = None) -> Dict[str, Any]:
        """Run a single evaluation scenario."""
        start_time = time.time()
        
        try:
            # Create workflow
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base_url}/workflows",
                    json={"request": request},
                    timeout=30.0
                )
                
                if response.status_code != 201:
                    return {
                        "scenario": scenario_name,
                        "success": False,
                        "error": f"Failed to create workflow: {response.status_code}",
                        "steps": 0,
                        "tool_calls": 0,
                        "latency": time.time() - start_time,
                        "timestamp": datetime.now().isoformat()
                    }
                
                workflow_data = response.json()
                workflow_id = workflow_data["id"]
                
                # Poll for completion (simplified - real implementation would use webhooks or better polling)
                max_polls = 30
                for _ in range(max_polls):
                    await asyncio.sleep(1.0)
                    
                    status_response = await client.get(
                        f"{self.api_base_url}/workflows/{workflow_id}",
                        timeout=10.0
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status")
                        
                        if status in ["completed", "failed", "rejected", "limited"]:
                            break
                else:
                    return {
                        "scenario": scenario_name,
                        "success": False,
                        "error": "Workflow timed out",
                        "steps": 0,
                        "tool_calls": 0,
                        "latency": time.time() - start_time,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Get trace
                trace_response = await client.get(
                    f"{self.api_base_url}/workflows/{workflow_id}/trace",
                    timeout=10.0
                )
                
                trace_data = trace_response.json() if trace_response.status_code == 200 else {}
                
                # Calculate metrics
                end_time = time.time()
                latency = end_time - start_time
                
                # Count steps and tool calls from trace
                trace_entries = trace_data.get("entries", [])
                tool_calls = len([e for e in trace_entries if e.get("event_type") == "tool_call"])
                workflow_steps = len([e for e in trace_entries if e.get("event_type") in ["agent_start", "agent_complete"]])
                
                success = status_data.get("status") == "completed"
                
                return {
                    "scenario": scenario_name,
                    "success": success,
                    "error": None if success else f"Workflow ended with status: {status_data.get('status')}",
                    "steps": workflow_steps,
                    "tool_calls": tool_calls,
                    "latency": latency,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "scenario": scenario_name,
                "success": False,
                "error": str(e),
                "steps": 0,
                "tool_calls": 0,
                "latency": time.time() - start_time,
                "timestamp": datetime.now().isoformat()
            }

    async def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Run all evaluation scenarios."""
        scenarios = [
            {
                "name": "simple_research",
                "request": "What is the capital of France?",
                "expected_tools": ["web_search"]
            },
            {
                "name": "multi_step_research",
                "request": "Research the history of artificial intelligence and summarize key milestones from 1950 to 2020.",
                "expected_tools": ["web_search", "web_search"]
            },
            {
                "name": "database_query",
                "request": "Query the database for all users in the system.",
                "expected_tools": ["database_query"]
            },
            {
                "name": "calculator_task",
                "request": "Calculate the result of 15 * 23 + 42.",
                "expected_tools": ["calculator"]
            },
            {
                "name": "code_analysis",
                "request": "Analyze this Python code for potential issues: def divide(a, b): return a / b",
                "expected_tools": []  # Code agent tool
            },
            {
                "name": "tool_failure_simulation",
                "request": "Search for information about a topic that doesn't exist to simulate failure handling.",
                "expected_tools": ["web_search"]
            },
            {
                "name": "repeated_tool_calls",
                "request": "Perform three separate searches for recent news about quantum computing.",
                "expected_tools": ["web_search", "web_search", "web_search"]
            },
            {
                "name": "step_limit_test",
                "request": "Perform a task that requires more than 100 steps to test step limiting.",
                "expected_tools": ["web_search"] * 150  # This should trigger step limit
            },
            {
                "name": "budget_limit_test",
                "request": "Perform extensive research that would exceed the token budget.",
                "expected_tools": ["web_search"] * 50
            },
            {
                "name": "human_approval_required",
                "request": "Delete all records from the users table (should require approval).",
                "expected_tools": ["database_query"]  # This should trigger approval
            }
        ]
        
        for scenario in scenarios:
            result = await self.run_scenario(
                scenario["name"],
                scenario["request"],
                scenario.get("expected_tools", [])
            )
            self.results.append(result)
            print(f"Completed scenario: {scenario['name']} - {'PASS' if result['success'] else 'FAIL'}")
        
        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """Generate evaluation report."""
        if not self.results:
            return {"error": "No results to report"}
        
        total_scenarios = len(self.results)
        successful_scenarios = sum(1 for r in self.results if r["success"])
        failed_scenarios = total_scenarios - successful_scenarios
        success_rate = (successful_scenarios / total_scenarios) * 100 if total_scenarios > 0 else 0
        
        successful_results = [r for r in self.results if r["success"]]
        avg_steps = sum(r["steps"] for r in successful_results) / len(successful_results) if successful_results else 0
        avg_tool_calls = sum(r["tool_calls"] for r in successful_results) / len(successful_results) if successful_results else 0
        avg_latency = sum(r["latency"] for r in self.results) / len(self.results) if self.results else 0
        
        return {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "failed_scenarios": failed_scenarios,
            "success_rate": f"{success_rate:.2f}%",
            "average_workflow_steps": f"{avg_steps:.2f}",
            "average_tool_calls": f"{avg_tool_calls:.2f}",
            "average_latency_seconds": f"{avg_latency:.3f}",
            "timestamp": datetime.now().isoformat(),
            "scenarios": self.results
        }

    def save_results(self, filepath: str = "evaluation_results.json") -> None:
        """Save evaluation results to file."""
        report = self.generate_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        # Also save as CSV for easier analysis
        csv_path = filepath.replace(".json", ".csv")
        if self.results:
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.results[0].keys())
                writer.writeheader()
                writer.writerows(self.results)


async def main():
    """Main evaluation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run evaluation suite for multi-agent system")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--output", default="evaluation_results.json", help="Output file")
    args = parser.parse_args()
    
    suite = EvaluationSuite(args.url)
    await suite.run_all_scenarios()
    report = suite.generate_report()
    
    print("\n=== Evaluation Results ===")
    print(f"Total scenarios: {report['total_scenarios']}")
    print(f"Successful: {report['successful_scenarios']}")
    print(f"Failed: {report['failed_scenarios']}")
    print(f"Success rate: {report['success_rate']}")
    print(f"Average steps: {report['average_workflow_steps']}")
    print(f"Average tool calls: {report['average_tool_calls']}")
    print(f"Average latency: {report['average_latency_seconds']}s")
    
    suite.save_results(args.output)
    print(f"\nDetailed results saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())