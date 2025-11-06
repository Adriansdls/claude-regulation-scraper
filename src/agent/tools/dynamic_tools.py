"""Dynamic code execution tools.

Allows the agent to write and execute custom NetworkX code for analyses
that aren't covered by pre-defined tools.
"""

from typing import Dict, Any
from ...analysis import DynamicGraphQueryExecutor


class DynamicGraphQueryTool:
    """
    Execute custom NetworkX code for novel analyses.

    This is the POWER TOOL - lets the agent write custom graph analysis code
    when pre-defined tools aren't sufficient. The LLM is excellent at NetworkX!
    """

    name = "dynamic_graph_query"
    description = """
    Execute custom NetworkX code for complex or novel analyses.

    Use this when:
    - Pre-defined tools don't cover your specific analysis need
    - You need to combine multiple operations in a custom way
    - The query requires complex filtering or custom logic
    - You want to implement a specific algorithm not available

    You can write NetworkX code that has access to:
    - kg.paper_graph: Citation network (NetworkX DiGraph)
    - kg.concept_graph: Concept network (NetworkX MultiDiGraph)
    - kg.papers: Dict of Paper objects (kg.papers[paper_id])
    - kg.entities: Dict of Entity objects (kg.entities[entity_id])
    - kg.relationships: Dict of Relationship objects
    - nx: NetworkX library (import networkx as nx)
    - np: NumPy library
    - Standard Python: collections, itertools, math, statistics

    IMPORTANT: Your code must set a 'result' variable with the output.

    Parameters:
    - code: Python code to execute (string)
    - description: What the code does (for logging)

    Example code patterns:

    # Find papers citing both A and B:
    code = '''
    citers_a = set(kg.paper_graph.predecessors(paper_a_id))
    citers_b = set(kg.paper_graph.predecessors(paper_b_id))
    both = citers_a & citers_b
    result = [kg.papers[pid].title for pid in both if pid in kg.papers]
    '''

    # Calculate clustering coefficient:
    code = '''
    G = kg.paper_graph.to_undirected()
    clustering = nx.clustering(G)
    result = {
        'avg': sum(clustering.values()) / len(clustering),
        'top': sorted(clustering.items(), key=lambda x: x[1], reverse=True)[:10]
    }
    '''

    # Count papers by year:
    code = '''
    from collections import Counter
    years = Counter(p.year for p in kg.papers.values() if p.year)
    result = sorted(years.items())
    '''

    Safety: Code is executed in a sandbox with 30-second timeout, no file access,
    and restricted imports. Only safe operations are allowed.

    Returns execution result with the computed value, stdout, and execution time.
    """

    def __init__(self, executor: DynamicGraphQueryExecutor):
        self.executor = executor

    def __call__(self, code: str, description: str = "") -> Dict[str, Any]:
        """Execute dynamic graph query."""
        try:
            response = self.executor.query(
                code=code,
                description=description,
                explain=True
            )

            if not response["success"]:
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error"),
                    "error_type": response.get("error_type", "ExecutionError"),
                    "code": code,
                    "description": description
                }

            return {
                "success": True,
                "result": response["result"],
                "description": description,
                "execution_time": response["execution_time"],
                "stdout": response.get("stdout", ""),
                "interpretation": self._interpret_results(response, description)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "code": code
            }

    def _interpret_results(self, response, description) -> str:
        """Generate human-readable interpretation."""
        exec_time = response.get("execution_time", "")
        result_type = type(response["result"]).__name__

        if result_type == "list":
            count = len(response["result"])
            return f"Query executed successfully in {exec_time}. Returned {count} results."
        elif result_type == "dict":
            keys = len(response["result"])
            return f"Query executed successfully in {exec_time}. Returned dictionary with {keys} keys."
        else:
            return f"Query executed successfully in {exec_time}. Returned {result_type}."


class GetGraphInfoTool:
    """
    Get information about what data is available in the knowledge graph.

    Helps the agent understand what it can query and analyze.
    """

    name = "get_graph_info"
    description = """
    Get information about the knowledge graph structure and available data.

    Use this when you need to:
    - Understand what data is available
    - Check the size and structure of the graph
    - See what types of entities and relationships exist
    - Learn what you can query

    Returns:
    - Number of papers, entities, relationships
    - Entity types and their counts
    - Relationship types and their counts
    - Graph sizes (nodes, edges)
    - Available data structures and access patterns

    This helps you write better queries by knowing what data exists.
    """

    def __init__(self, executor: DynamicGraphQueryExecutor):
        self.executor = executor

    def __call__(self) -> Dict[str, Any]:
        """Get knowledge graph information."""
        try:
            info = self.executor.get_available_data()

            return {
                "success": True,
                "knowledge_graph": info["knowledge_graph"],
                "graphs": info["graphs"],
                "available_libraries": info["available_libraries"],
                "code_examples": info.get("code_pattern", ""),
                "interpretation": self._interpret_results(info)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _interpret_results(self, info) -> str:
        """Generate human-readable interpretation."""
        kg = info["knowledge_graph"]
        graphs = info["graphs"]

        papers = kg["papers"]["count"]
        entities = kg["entities"]["count"]
        entity_types = len(kg["entities"]["types"])

        paper_graph = graphs["paper_graph"]
        concept_graph = graphs["concept_graph"]

        return (
            f"Knowledge graph contains {papers} papers and {entities} entities "
            f"of {entity_types} types. The citation network has {paper_graph['nodes']} nodes "
            f"and {paper_graph['edges']} edges. The concept network has {concept_graph['nodes']} nodes "
            f"and {concept_graph['edges']} edges."
        )
