# Agent Interface

> Reference for `research` skill. Load when the skill is called by another agent (not directly by user).

## Input from the calling agent

```
topic: string                    # Topic to research
research_angle: string           # "overview" | "technical" | "comparison" | "problems" | "best_practices"
depth: "quick" | "standard" | "deep" | "iterative_deep"   # Default: standard
output_mode: "structured" | "file" | "inline"  # Default: structured
save_path: string (optional)     # If output_mode = "file"
```

## Output to the calling agent (structured mode)

```json
{
  "topic": "...",
  "angle": "...",
  "rounds_completed": 1,
  "top_insights": [
    {"claim": "insight 1", "confidence": "✅|⚡|⚠|⚡|❌", "sources": 2}
  ],
  "consensus_points": ["points that most sources agree on"],
  "contested_points": [
    {"claim": "...", "view_a": "...", "view_b": "...", "confidence": "⚡"}
  ],
  "refuted_claims": ["claims that were refuted during verification"],
  "gaps_filled_by_round": {
    "round_1": ["gap 1 filled", "gap 2 filled"],
    "round_2": ["gap 3 filled"],
    "round_3": []
  },
  "remaining_gaps": ["what still doesn't have a clear answer"],
  "recommended_approach": "...",
  "sources": [
    {"url": "...", "tier": 1, "round": 1, "claims": ["claim 1"], "summary": "..."}
  ],
  "gaps": ["what the research hasn't covered"]
}
```
