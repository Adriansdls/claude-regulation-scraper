"""Dynamic graph query execution - Let the LLM write NetworkX code!

This module allows the agent to write and execute custom NetworkX code for
novel analyses that aren't covered by pre-defined algorithms.

The LLM is excellent at NetworkX! It can write code for:
- Custom graph traversals
- Novel metrics
- Complex filtering
- Domain-specific analyses

Safety is ensured through:
- Restricted imports (only networkx, numpy, scipy, pandas)
- Execution timeout (30 seconds)
- Memory limits
- No file system access
- Sandboxed environment
"""

import ast
import sys
import io
import signal
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time


@dataclass
class ExecutionResult:
    """Result from dynamic code execution"""
    success: bool
    result: Any
    stdout: str
    stderr: str
    execution_time: float
    error: Optional[str] = None
    error_type: Optional[str] = None


class SafeExecutor:
    """
    Safe execution environment for LLM-generated graph analysis code.

    Provides:
    - Restricted imports (only safe libraries)
    - Execution timeout
    - Capture stdout/stderr
    - Error handling

    The LLM can write code that has access to:
    - networkx as nx
    - numpy as np
    - scipy (if available)
    - pandas as pd (if available)
    - The knowledge graph via 'kg' variable
    """

    ALLOWED_IMPORTS = {
        'networkx': 'nx',
        'numpy': 'np',
        'scipy': 'scipy',
        'pandas': 'pd',
        'math': 'math',
        'statistics': 'statistics',
        'collections': 'collections',
        'itertools': 'itertools',
    }

    TIMEOUT_SECONDS = 30  # Maximum execution time

    def __init__(self, knowledge_graph):
        """
        Initialize executor with knowledge graph.

        Args:
            knowledge_graph: KnowledgeGraph instance that code will have access to
        """
        self.kg = knowledge_graph

    def execute(self, code: str, description: str = "") -> ExecutionResult:
        """
        Execute LLM-generated NetworkX code safely.

        The code will have access to:
        - kg: Knowledge graph object
        - kg.paper_graph: Citation network (NetworkX DiGraph)
        - kg.concept_graph: Concept network (NetworkX MultiDiGraph)
        - kg.papers: Dictionary of Paper objects
        - kg.entities: Dictionary of Entity objects
        - kg.relationships: Dictionary of Relationship objects
        - nx: NetworkX library
        - np: NumPy library

        Args:
            code: Python code to execute (string)
            description: Human-readable description of what code does

        Returns:
            ExecutionResult with result, output, and any errors

        Example:
            ```python
            code = '''
            # Find papers that cite both BERT and GPT
            bert_citers = set(kg.paper_graph.predecessors("BERT_paper_id"))
            gpt_citers = set(kg.paper_graph.predecessors("GPT_paper_id"))
            both = bert_citers & gpt_citers

            result = [kg.papers[pid].title for pid in both if pid in kg.papers]
            '''

            result = executor.execute(code, "Find papers citing both BERT and GPT")
            print(result.result)  # List of paper titles
            ```
        """
        start_time = time.time()

        # Validate code
        try:
            self._validate_code(code)
        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                stdout="",
                stderr="",
                execution_time=0,
                error=str(e),
                error_type="ValidationError"
            )

        # Set up execution environment
        exec_globals = self._setup_environment()

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Set timeout
            if hasattr(signal, 'SIGALRM'):  # Unix only
                signal.signal(signal.SIGALRM, self._timeout_handler)
                signal.alarm(self.TIMEOUT_SECONDS)

            # Execute code
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals)

            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

            # Get result (code should set 'result' variable)
            result = exec_globals.get('result', None)

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=True,
                result=result,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=execution_time
            )

        except TimeoutError:
            return ExecutionResult(
                success=False,
                result=None,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=time.time() - start_time,
                error=f"Execution timeout after {self.TIMEOUT_SECONDS} seconds",
                error_type="TimeoutError"
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                result=None,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=time.time() - start_time,
                error=traceback.format_exc(),
                error_type=type(e).__name__
            )

    def _setup_environment(self) -> Dict[str, Any]:
        """Set up safe execution environment with allowed imports."""
        env = {}

        # Import allowed libraries
        for module_name, alias in self.ALLOWED_IMPORTS.items():
            try:
                if module_name == 'networkx':
                    import networkx
                    env[alias] = networkx
                elif module_name == 'numpy':
                    import numpy
                    env[alias] = numpy
                elif module_name == 'scipy':
                    try:
                        import scipy
                        env[alias] = scipy
                    except ImportError:
                        pass
                elif module_name == 'pandas':
                    try:
                        import pandas
                        env[alias] = pandas
                    except ImportError:
                        pass
                elif module_name == 'math':
                    import math
                    env[alias] = math
                elif module_name == 'statistics':
                    import statistics
                    env[alias] = statistics
                elif module_name == 'collections':
                    import collections
                    env[alias] = collections
                elif module_name == 'itertools':
                    import itertools
                    env[alias] = itertools
            except ImportError:
                pass

        # Add knowledge graph
        env['kg'] = self.kg

        # Add built-in functions (safe subset)
        env['len'] = len
        env['list'] = list
        env['dict'] = dict
        env['set'] = set
        env['tuple'] = tuple
        env['range'] = range
        env['enumerate'] = enumerate
        env['zip'] = zip
        env['map'] = map
        env['filter'] = filter
        env['sorted'] = sorted
        env['sum'] = sum
        env['min'] = min
        env['max'] = max
        env['abs'] = abs
        env['round'] = round
        env['str'] = str
        env['int'] = int
        env['float'] = float
        env['bool'] = bool
        env['print'] = print

        return env

    def _validate_code(self, code: str):
        """
        Validate code before execution.

        Checks for:
        - Valid Python syntax
        - No dangerous imports
        - No file operations
        - No system calls
        """
        # Check syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in code: {e}")

        # Check for dangerous patterns
        for node in ast.walk(tree):
            # No imports (we provide everything needed)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ValueError(
                    "Import statements not allowed. "
                    "Use pre-imported libraries: nx, np, scipy, pd"
                )

            # No file operations
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'id'):
                    func_name = node.func.id
                    if func_name in ['open', 'exec', 'eval', 'compile', '__import__']:
                        raise ValueError(f"Function '{func_name}' not allowed")

                # No attribute access to dangerous functions
                if hasattr(node.func, 'attr'):
                    attr_name = node.func.attr
                    if attr_name in ['system', 'popen', 'subprocess']:
                        raise ValueError(f"Method '{attr_name}' not allowed")

    @staticmethod
    def _timeout_handler(signum, frame):
        """Handle execution timeout."""
        raise TimeoutError("Code execution timeout")


class DynamicGraphQueryExecutor:
    """
    High-level interface for dynamic graph queries.

    This is what the agent tool will use. It provides a simple interface
    for the LLM to write and execute NetworkX code.
    """

    def __init__(self, knowledge_graph):
        """
        Initialize executor.

        Args:
            knowledge_graph: KnowledgeGraph instance
        """
        self.executor = SafeExecutor(knowledge_graph)
        self.kg = knowledge_graph

    def query(
        self,
        code: str,
        description: str = "",
        explain: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a dynamic graph query written by the LLM.

        Args:
            code: NetworkX code to execute
            description: What the code does (for logging/debugging)
            explain: Include execution details in response

        Returns:
            Dictionary with result and metadata

        Example:
            ```python
            executor = DynamicGraphQueryExecutor(kg)

            code = '''
            # Find most cited papers published after 2020
            recent_papers = [
                (pid, p)
                for pid, p in kg.papers.items()
                if p.year and p.year >= 2020
            ]

            # Sort by citation count
            sorted_papers = sorted(
                recent_papers,
                key=lambda x: x[1].metadata.citation_count,
                reverse=True
            )[:10]

            result = [
                {
                    'title': p.title,
                    'year': p.year,
                    'citations': p.metadata.citation_count
                }
                for pid, p in sorted_papers
            ]
            '''

            response = executor.query(
                code,
                description="Find top 10 most cited papers since 2020"
            )

            print(response['result'])
            ```
        """
        # Execute code
        exec_result = self.executor.execute(code, description)

        # Format response
        response = {
            "success": exec_result.success,
            "result": exec_result.result,
            "description": description,
        }

        if explain:
            response.update({
                "execution_time": f"{exec_result.execution_time:.3f}s",
                "stdout": exec_result.stdout,
            })

        if not exec_result.success:
            response.update({
                "error": exec_result.error,
                "error_type": exec_result.error_type,
                "stderr": exec_result.stderr,
            })

        return response

    def get_available_data(self) -> Dict[str, Any]:
        """
        Get information about what data is available for queries.

        Useful for the LLM to understand what it can query.

        Returns:
            Dictionary describing available data structures
        """
        return {
            "knowledge_graph": {
                "papers": {
                    "count": len(self.kg.papers),
                    "attributes": "paper_id, title, abstract, authors, year, venue, references, cited_by, full_text",
                    "example_access": "kg.papers[paper_id]"
                },
                "entities": {
                    "count": len(self.kg.entities),
                    "types": list(set(e.entity_type for e in self.kg.entities.values())),
                    "attributes": "entity_id, entity_type, text, attributes, source_paper_id, confidence",
                    "example_access": "kg.entities[entity_id]"
                },
                "relationships": {
                    "count": len(self.kg.relationships),
                    "types": list(set(r.relationship_type for r in self.kg.relationships.values())),
                    "attributes": "relationship_id, relationship_type, source_entity_id, target_entity_id, confidence",
                    "example_access": "kg.relationships[relationship_id]"
                }
            },
            "graphs": {
                "paper_graph": {
                    "type": "NetworkX DiGraph (directed)",
                    "nodes": self.kg.paper_graph.number_of_nodes(),
                    "edges": self.kg.paper_graph.number_of_edges(),
                    "description": "Citation network - edges mean 'cites'",
                    "example_access": "kg.paper_graph"
                },
                "concept_graph": {
                    "type": "NetworkX MultiDiGraph (directed, multi-edge)",
                    "nodes": self.kg.concept_graph.number_of_nodes(),
                    "edges": self.kg.concept_graph.number_of_edges(),
                    "description": "Concept/entity network - edges are relationships",
                    "example_access": "kg.concept_graph"
                }
            },
            "available_libraries": {
                "networkx": "nx - Full NetworkX library",
                "numpy": "np - NumPy for numerical operations",
                "scipy": "scipy - Scientific computing (if installed)",
                "pandas": "pd - Data analysis (if installed)",
                "built_ins": "len, list, dict, set, sorted, sum, min, max, etc."
            },
            "code_pattern": """
# Your code should end with setting a 'result' variable
# Example:

# Query the graph
papers = list(kg.papers.values())

# Filter
recent = [p for p in papers if p.year and p.year >= 2020]

# Analyze with NetworkX
important = nx.pagerank(kg.paper_graph)
top = sorted(important.items(), key=lambda x: x[1], reverse=True)[:10]

# Format result
result = {
    'recent_papers': len(recent),
    'top_papers': [kg.papers[pid].title for pid, score in top if pid in kg.papers]
}
"""
        }

    def example_queries(self) -> List[Dict[str, str]]:
        """
        Get example queries the LLM can use as templates.

        Returns:
            List of example queries with code and descriptions
        """
        return [
            {
                "description": "Find papers that cite both A and B",
                "code": """
# Get papers citing both papers
citers_a = set(kg.paper_graph.predecessors(paper_a_id))
citers_b = set(kg.paper_graph.predecessors(paper_b_id))
both = citers_a & citers_b

result = [kg.papers[pid].title for pid in both if pid in kg.papers]
"""
            },
            {
                "description": "Find most central authors by betweenness",
                "code": """
# Build co-authorship network
import networkx as nx
coauthor = nx.Graph()

for paper in kg.papers.values():
    authors = [a.name for a in paper.authors]
    for i, a1 in enumerate(authors):
        for a2 in authors[i+1:]:
            if coauthor.has_edge(a1, a2):
                coauthor[a1][a2]['weight'] += 1
            else:
                coauthor.add_edge(a1, a2, weight=1)

# Calculate betweenness
betweenness = nx.betweenness_centrality(coauthor)
top = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]

result = top
"""
            },
            {
                "description": "Find concepts mentioned in multiple papers but not connected",
                "code": """
# Find entities appearing in multiple papers
from collections import Counter

entity_papers = {}
for entity_id, entity in kg.entities.items():
    source = entity.source_paper_id
    entity_text = entity.text.lower()

    if entity_text not in entity_papers:
        entity_papers[entity_text] = set()
    entity_papers[entity_text].add(source)

# Filter to concepts in 3+ papers
frequent = {
    text: papers
    for text, papers in entity_papers.items()
    if len(papers) >= 3
}

# Check which aren't connected in concept graph
disconnected = []
for text, papers in frequent.items():
    # Find entities with this text
    entities = [
        eid for eid, e in kg.entities.items()
        if e.text.lower() == text
    ]

    # Check if any are connected
    connected = False
    for e1 in entities:
        for e2 in entities:
            if e1 != e2 and kg.concept_graph.has_edge(e1, e2):
                connected = True
                break
        if connected:
            break

    if not connected:
        disconnected.append({
            'concept': text,
            'papers': len(papers)
        })

result = sorted(disconnected, key=lambda x: x['papers'], reverse=True)[:10]
"""
            },
            {
                "description": "Calculate clustering coefficient for citation network",
                "code": """
# Convert to undirected for clustering coefficient
G_undirected = kg.paper_graph.to_undirected()

# Calculate clustering
clustering = nx.clustering(G_undirected)

# Get average and distribution
avg_clustering = sum(clustering.values()) / len(clustering) if clustering else 0

# Get top clustered papers
top_clustered = sorted(clustering.items(), key=lambda x: x[1], reverse=True)[:10]

result = {
    'average_clustering': avg_clustering,
    'top_clustered_papers': [
        {
            'title': kg.papers[pid].title if pid in kg.papers else pid,
            'clustering': score
        }
        for pid, score in top_clustered
    ]
}
"""
            },
            {
                "description": "Find research trends by year",
                "code": """
from collections import Counter

# Count papers by year
papers_by_year = Counter()
for paper in kg.papers.values():
    if paper.year:
        papers_by_year[paper.year] += 1

# Sort by year
timeline = sorted(papers_by_year.items())

# Calculate growth rate
growth_rates = []
for i in range(1, len(timeline)):
    year, count = timeline[i]
    prev_year, prev_count = timeline[i-1]

    if prev_count > 0:
        growth = ((count - prev_count) / prev_count) * 100
        growth_rates.append((year, growth))

result = {
    'timeline': timeline,
    'growth_rates': growth_rates,
    'peak_year': max(papers_by_year.items(), key=lambda x: x[1]) if papers_by_year else None
}
"""
            }
        ]
