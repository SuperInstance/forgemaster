"""Fleet operations plugin for AutoData — Cocapn fleet integration.

Provides tools for querying PLATO knowledge rooms, constraint-theory CSP
solving, and underwater sonar physics calculations. Injects prompt guidance
into PlanAgent and EngineerAgent to leverage fleet knowledge and constraint
validation throughout AutoData workflows.
"""

from __future__ import annotations

import json
import math
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from autodata.plugins import PluginSpec

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLATO_BASE_URL = "http://147.224.38.131:8847"

# Mackenzie (1981) equation coefficients for sound speed in seawater
#   c = 1448.96 + 4.591T - 5.304e-2 T² + 2.374e-4 T³
#       + 1.340(S - 35) + 1.630e-2 D + 1.675e-7 D²
#       - 1.025e-2 T(S - 35) - 7.139e-13 T D³
# where T = temp °C, S = salinity PSU, D = depth m

# Francois-Garrison (1982) simplified coefficients for absorption (dB/km)
# Approximation valid for 0.4 – 1000 kHz range


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class FleetKnowledgeInput(BaseModel):
    room: str = Field(
        ..., description="PLATO room name to query (e.g., 'work-log', 'milestones', 'decisions')"
    )
    query: str | None = Field(
        default=None,
        description="Optional search term to filter entries within the room",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of entries to return",
    )


class ConstraintTheoryInput(BaseModel):
    variables: list[str] = Field(
        ..., description="Names of the decision variables in the CSP"
    )
    domains: dict[str, list[Any]] = Field(
        ..., description="Mapping of variable name → list of allowed values"
    )
    constraints: list[str] = Field(
        ..., description="Constraint expressions (each a Python-evaluable string using variable names)"
    )
    method: str = Field(
        default="backtracking",
        description="Solver method: 'backtracking', 'forward_checking', or 'arc_consistency'",
    )


class SonarVisionInput(BaseModel):
    depth: float = Field(
        ..., ge=0, description="Depth in metres below the surface"
    )
    temperature: float = Field(
        default=10.0,
        ge=-2,
        le=40,
        description="Water temperature in °C at the specified depth",
    )
    salinity: float = Field(
        default=35.0,
        ge=0,
        le=45,
        description="Salinity in PSU (practical salinity units)",
    )
    frequency_khz: float = Field(
        default=50.0,
        gt=0,
        description="Sonar frequency in kHz for absorption calculation",
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class FleetKnowledgeTool(BaseTool):
    """Query PLATO knowledge rooms for fleet context, decisions, and work logs."""

    name: str = "fleet_knowledge_tool"
    description: str = (
        "Query the Cocapn fleet's PLATO knowledge base for work logs, decisions, "
        "milestones, blockers, and architectural context stored in named rooms."
    )
    args_schema: type[BaseModel] = FleetKnowledgeInput

    def _run(
        self,
        room: str,
        query: str | None = None,
        limit: int = 10,
    ) -> str:
        try:
            resp = httpx.get(
                f"{PLATO_BASE_URL}/rooms/{room}",
                params={"q": query, "limit": limit},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return f"No entries found in PLATO room '{room}'."
            return json.dumps(data, indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as exc:
            return f"PLATO returned HTTP {exc.response.status_code} for room '{room}'."
        except httpx.ConnectError:
            return f"Unable to connect to PLATO at {PLATO_BASE_URL}. Is the service running?"
        except Exception as exc:  # pragma: no cover — defensive
            return f"PLATO query error: {exc}"

    async def _arun(
        self,
        room: str,
        query: str | None = None,
        limit: int = 10,
    ) -> str:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{PLATO_BASE_URL}/rooms/{room}",
                    params={"q": query, "limit": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    return f"No entries found in PLATO room '{room}'."
                return json.dumps(data, indent=2, ensure_ascii=False)
        except httpx.HTTPStatusError as exc:
            return f"PLATO returned HTTP {exc.response.status_code} for room '{room}'."
        except httpx.ConnectError:
            return f"Unable to connect to PLATO at {PLATO_BASE_URL}. Is the service running?"
        except Exception as exc:  # pragma: no cover
            return f"PLATO query error: {exc}"


class ConstraintTheoryTool(BaseTool):
    """Solve constraint satisfaction problems using constraint-theory primitives."""

    name: str = "constraint_theory_tool"
    description: str = (
        "Solve constraint satisfaction problems (CSPs) by specifying variables, "
        "domains, and constraint expressions. Supports backtracking, forward-checking, "
        "and arc-consistency methods."
    )
    args_schema: type[BaseModel] = ConstraintTheoryInput

    def _run(
        self,
        variables: list[str],
        domains: dict[str, list[Any]],
        constraints: list[str],
        method: str = "backtracking",
    ) -> str:
        try:
            from constraint_theory import CSPSolver  # type: ignore[import-untyped]
        except ImportError:
            # Fallback: lightweight built-in backtracking solver
            return self._solve_builtin(variables, domains, constraints, method)

        solver = CSPSolver(method=method)
        for var in variables:
            solver.add_variable(var, domains.get(var, []))
        for expr in constraints:
            solver.add_constraint(expr)
        solutions = solver.solve()
        if not solutions:
            return "No solution found — the CSP is unsatisfiable under the given constraints."
        return json.dumps(
            {"solution_count": len(solutions), "solutions": solutions[:10]},
            indent=2,
        )

    async def _arun(
        self,
        variables: list[str],
        domains: dict[str, list[Any]],
        constraints: list[str],
        method: str = "backtracking",
    ) -> str:
        return self._run(variables, domains, constraints, method)

    # -- lightweight built-in backtracker when constraint_theory is absent --

    @staticmethod
    def _solve_builtin(
        variables: list[str],
        domains: dict[str, list[Any]],
        constraints: list[str],
        method: str,
    ) -> str:
        """Minimal backtracking CSP solver for when constraint_theory is not installed."""
        assignment: dict[str, Any] = {}
        solutions: list[dict[str, Any]] = []

        def is_consistent() -> bool:
            for expr in constraints:
                try:
                    if not eval(expr, {"__builtins__": {}}, assignment):  # noqa: S307
                        return False
                except Exception:
                    # Incomplete assignment — skip
                    pass
            return True

        def backtrack(idx: int) -> None:
            if idx == len(variables):
                if is_consistent():
                    solutions.append(dict(assignment))
                return
            var = variables[idx]
            for val in domains.get(var, []):
                assignment[var] = val
                if is_consistent():
                    backtrack(idx + 1)
                del assignment[var]

        backtrack(0)
        if not solutions:
            return "No solution found — the CSP is unsatisfiable under the given constraints."
        return json.dumps(
            {
                "solver": f"builtin-{method}",
                "solution_count": len(solutions),
                "solutions": solutions[:10],
            },
            indent=2,
        )


class SonarVisionTool(BaseTool):
    """Calculate underwater acoustic properties — sound speed and absorption at depth."""

    name: str = "sonar_vision_tool"
    description: str = (
        "Compute sound speed in seawater (Mackenzie 1981 equation) and acoustic "
        "absorption (Francois-Garrison 1982) at a given depth, temperature, salinity, "
        "and frequency."
    )
    args_schema: type[BaseModel] = SonarVisionInput

    def _run(
        self,
        depth: float,
        temperature: float = 10.0,
        salinity: float = 35.0,
        frequency_khz: float = 50.0,
    ) -> str:
        T = temperature
        S = salinity
        D = depth

        # Mackenzie (1981) sound speed equation
        c = (
            1448.96
            + 4.591 * T
            - 5.304e-2 * T ** 2
            + 2.374e-4 * T ** 3
            + 1.340 * (S - 35)
            + 1.630e-2 * D
            + 1.675e-7 * D ** 2
            - 1.025e-2 * T * (S - 35)
            - 7.139e-13 * T * D ** 3
        )

        # Simplified Francois-Garrison (1982) absorption — dB/km
        f = frequency_khz  # kHz
        # Rough approximation: α ≈ 0.11 * f² / (1 + f²) + 44 * f² / (4100 + f²) + 2.75e-4 * f² + 0.003
        alpha = (
            0.11 * f ** 2 / (1 + f ** 2)
            + 44.0 * f ** 2 / (4100.0 + f ** 2)
            + 2.75e-4 * f ** 2
            + 0.003
        )

        # Wavelength
        wavelength = c / (f * 1000.0)  # metres

        result = {
            "depth_m": D,
            "temperature_c": T,
            "salinity_psu": S,
            "frequency_khz": f,
            "sound_speed_m_s": round(c, 2),
            "absorption_db_per_km": round(alpha, 4),
            "wavelength_m": round(wavelength, 4),
            "travel_time_to_depth_s": round(D / c, 6) if c > 0 else None,
        }
        return json.dumps(result, indent=2)

    async def _arun(
        self,
        depth: float,
        temperature: float = 10.0,
        salinity: float = 35.0,
        frequency_khz: float = 50.0,
    ) -> str:
        return self._run(depth, temperature, salinity, frequency_khz)


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

PLUGIN = PluginSpec(
    name="fleet",
    prompts={
        "PlanAgent": (
            "The Cocapn fleet uses PLATO as its external knowledge cortex. Before planning "
            "any workflow, consider querying PLATO rooms (work-log, decisions, milestones) "
            "via `fleet_knowledge_tool` to ground plans in existing context, prior decisions, "
            "and known blockers. Fleet knowledge is authoritative — treat PLATO as the source "
            "of truth for architectural context and operational state."
        ),
        "ToolAgent": (
            "Use `fleet_knowledge_tool` to query PLATO rooms for fleet decisions and context. "
            "Use `constraint_theory_tool` to solve constraint satisfaction problems when the "
            "task involves feasibility, scheduling, or resource allocation. Use "
            "`sonar_vision_tool` for underwater acoustic calculations (sound speed, absorption, "
            "wavelength at depth)."
        ),
        "EngineerAgent": (
            "When implementing pipeline code, validate all constraint-satisfaction results from "
            "`constraint_theory_tool` against the original problem specification. Ensure numeric "
            "tolerances are explicit and that CSP solutions are verified before downstream use. "
            "For sonar/underwater physics, use Mackenzie (1981) sound speed and Francois-Garrison "
            "(1982) absorption models — document which equations are in play."
        ),
        "ValidationAgent": (
            "Verify that PLATO-sourced context is current (check timestamps). Confirm CSP solutions "
            "satisfy all stated constraints. Validate sonar physics outputs against expected ranges: "
            "sound speed ~1450–1550 m/s, absorption increasing with frequency and depth."
        ),
    },
    tool_classes=(FleetKnowledgeTool, ConstraintTheoryTool, SonarVisionTool),
    metadata={
        "version": "1.0.0",
        "tool_info": {
            "fleet_knowledge_tool": (
                "Queries PLATO knowledge rooms for fleet work logs, decisions, milestones, and blockers."
            ),
            "constraint_theory_tool": (
                "Solves CSPs with backtracking, forward-checking, or arc-consistency methods."
            ),
            "sonar_vision_tool": (
                "Computes underwater sound speed (Mackenzie 1981) and absorption (Francois-Garrison 1982)."
            ),
        },
    },
)

__all__ = ["PLUGIN"]
