"""Task dependency handling - DAG resolution for the control plane.

Supports:
- Dependency graph construction from task metadata
- Topological sort for execution ordering
- Cycle detection
- Blocked task tracking
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class DependencyGraph:
    """Directed acyclic graph of task dependencies.

    Each node is a task_id. Edges represent "depends on" relationships.
    A task cannot start until all its dependencies are in a terminal state.
    """

    def __init__(self) -> None:
        self._graph: dict[str, set[str]] = defaultdict(set)  # task -> deps
        self._reverse: dict[str, set[str]] = defaultdict(set)  # dep -> dependents
        self._task_states: dict[str, str] = {}

    def add_task(self, task_id: str, dependencies: list[str] | None = None) -> tuple[bool, str]:
        """Add a task with its dependencies. Returns (success, message)."""
        if dependencies:
            for dep in dependencies:
                self._graph[task_id].add(dep)
                self._reverse[dep].add(task_id)
        else:
            self._graph[task_id] = set()
        return (True, f"task {task_id} added with deps={list(self._graph.get(task_id, set()))}")

    def update_state(self, task_id: str, state: str) -> None:
        """Update the state of a task."""
        self._task_states[task_id] = state

    def get_ready_tasks(self) -> list[str]:
        """Return tasks whose dependencies are all in terminal states.

        A task is ready if:
        - All its dependencies exist and are in COMPLETED or FAILED state
        - Tasks with no dependencies are always ready
        """
        ready = []
        for task_id, deps in self._graph.items():
            if not deps:
                ready.append(task_id)
                continue
            all_terminal = all(
                self._task_states.get(dep) in ("COMPLETED", "FAILED")
                for dep in deps
            )
            if all_terminal:
                ready.append(task_id)
        return ready

    def get_blocked_tasks(self) -> list[str]:
        """Return tasks that are blocked by non-terminal dependencies."""
        blocked = []
        for task_id, deps in self._graph.items():
            if not deps:
                continue
            non_terminal = [dep for dep in deps if self._task_states.get(dep) not in ("COMPLETED", "FAILED")]
            if non_terminal:
                blocked.append((task_id, non_terminal))
        return blocked

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles using DFS. Returns list of cycles found."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in self._graph}
        cycles = []

        def dfs(node: str, path: list[str]) -> None:
            color[node] = GRAY
            path.append(node)
            for neighbor in self._graph.get(node, set()):
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)
            path.pop()
            color[node] = BLACK

        for node in self._graph:
            if color[node] == WHITE:
                dfs(node, [])
        return cycles

    def topological_sort(self) -> list[str] | None:
        """Return topological ordering of tasks. Returns None if cycle detected."""
        if self.detect_cycles():
            return None
        in_degree = defaultdict(int)
        for node in self._graph:
            if node not in in_degree:
                in_degree[node] = 0
            for dep in self._graph[node]:
                in_degree[node] += 1  # task depends on dep, so dep must come first

        queue = deque(n for n in self._graph if in_degree[n] == 0)
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in self._reverse.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        return result if len(result) == len(self._graph) else None

    def get_dependents(self, task_id: str) -> set[str]:
        """Get all tasks that depend on the given task (directly or transitively)."""
        visited = set()
        queue = deque([task_id])
        while queue:
            node = queue.popleft()
            for dep in self._reverse.get(node, set()):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return visited

    def get_dependencies(self, task_id: str) -> set[str]:
        """Get direct dependencies of a task."""
        return set(self._graph.get(task_id, set()))

    @property
    def all_tasks(self) -> list[str]:
        return list(self._graph.keys())

    @property
    def task_states(self) -> dict[str, str]:
        return dict(self._task_states)
