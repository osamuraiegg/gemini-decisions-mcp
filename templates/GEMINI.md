# Global Rules

## System One (Google Gemini Decisions API / gemini-decision-1) Decision Guidance

The environment provides a high-speed, calibrated System One decision engine via the `gemini-decisions` MCP server powered by Google's `gemini-decision-1` model (supporting up to 256K tokens, zero output tokens, and full multimodal input including Excel `.xlsx`, Word `.docx`, PowerPoint `.pptx`, PDF, images, audio, and video).

Whenever you need fast, calibrated, objective decisions rather than generative text output, utilize the `gemini-decisions` tools (`decision_noul`, `decision_choice`, `decision_score`, `decision_evaluate`):

1. **Risk Gating (Action Check)**: Before executing potentially destructive shell commands, heavy refactorings, or migrations, evaluate the risk using `decision_noul` or the `system-one-decision` skill.
2. **Task Triaging & Routing**: When faced with complex bug reports, logs, or ambiguous multi-step tasks, classify the issue domain or choose the strategy using `decision_choice`.
3. **Objective Quality Scoring**: When evaluating code quality, security impact, or plan feasibility, score it against an explicit rubric using `decision_score`.
4. **Specification & Document Review (2-Stage Hybrid Review)**: When asked to review external specifications or design documents against source code, execute a 2-stage review:
   - **Stage 1**: Run `decision_evaluate` across a comprehensive checklist (constants match, API coverage, state transitions, exception handling, boundary conditions) to objectively flag discrepancies.
   - **Stage 2**: Formulate concrete, detailed review comments and generate corrected Markdown diffs for any identified discrepancies.
5. **Office & Tabular Data Audit**: When auditing spreadsheets (`.xlsx`) or data files, pass file paths directly to `decision_noul` or `decision_choice` (strict MIME typing is handled automatically).
6. **Test Result Verification & Report Generation**: Evaluate test execution logs, traces, or run evidence using `decision_noul` or `decision_score` to classify outcomes (`PASS` / `FAIL` / `NEEDS_REVIEW`), compiling results into structured reports (Markdown, JSON, CSV).
7. **Refer to the `system-one-decision` skill** for detailed workflows, schemas, and threshold guidelines.
