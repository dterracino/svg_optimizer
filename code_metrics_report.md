# Code Metrics Refactoring Report

## Scope and configuration

- Target: `.`
- Configuration: `E:/svg_optimizer/tools/code_metrics.json`
- Default exclusions enabled: `true`
- Custom exclusions: none
- Thresholds: lines 500, code lines 500, classes 1, definition lines 100
- Reproduce: `python tools/code_metrics.py . --report`

## Executive summary

- Files scanned: 27
- Files with unresolved findings: 5
- Line findings: 0
- Class findings: 1
- Long-definition findings: 5
- Analysis errors: 0

## Refactoring candidates

### `svg_optimizer/parameter_optimizer.py`

- Long definition: 101 (limit 100, over by 1); function `binary_search_parameter`, lines 62-162
- Long definition: 117 (limit 100, over by 17); method `ParameterOptimizer.optimize`, lines 214-330

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `svg_optimizer/__main__.py`

- Long definition: 422 (limit 100, over by 322); function `main`, lines 43-464

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `svg_optimizer/cli.py`

- Long definition: 185 (limit 100, over by 85); function `parse_arguments`, lines 34-218

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `svg_optimizer/image_upscaler.py`

- Long definition: 119 (limit 100, over by 19); method `ImageUpscaler.upscale_image`, lines 201-319

Suggested investigation:

- Look for cohesive phases or helpers that can be extracted without changing behavior.

### `svg_optimizer/svg_border.py`

- Classes: 2 (limit 1, over by 1); `BorderGenerationError` (line 29), `SVGBorderGenerator` (line 33)

Suggested investigation:

- Check whether the classes are cohesive and intentionally colocated.

## Analysis errors

None.

## Accepted findings

- `svg_optimizer/parameter_optimizer.py`: classes 3 (limit 1); `OptimizationResult` (line 30), `SearchBounds` (line 44), `ParameterOptimizer` (line 169)
- `svg_optimizer/visual_logger.py`: classes 2 (limit 1); `ComparisonEntry` (line 28), `VisualLogger` (line 40)
- `tools/code_metrics.py`: classes 14 (limit 1); `ConfigError` (line 89), `ScanConfig` (line 94), `Thresholds` (line 103), `TerminalConfig` (line 111), `MarkdownReportConfig` (line 119), `EffectiveConfig` (line 126), `ClassMetric` (line 135), `DefinitionMetric` (line 141), `FileMetrics` (line 150), `Finding` (line 178), `FileReport` (line 189), `Summary` (line 203), `MetricsReport` (line 222), `_StructureVisitor` (line 541)
- `tools/code_metrics.py`: code_lines 790 (limit 500)
- `tools/code_metrics.py`: lines 930 (limit 500)

## Override comments and manual approval

File-wide source comments can accept intentional threshold findings:

```python
# code-metrics: accept lines -- reason for accepting the file's line counts.
# code-metrics: accept classes -- reason for keeping multiple classes together.
# code-metrics: accept monoliths -- reason for keeping long definitions together.
```

- `lines` accepts both physical-line and code-line findings in the file.
- `classes` accepts the class-count finding in the file.
- `monoliths` accepts every long-function or long-method finding in the file.
- Markers are case-insensitive and may include an explanatory reason after the category.
- Accepted findings retain their measured values but are not counted as unresolved and do not trigger `--fail-on-problems`.
- These comments do not override read, decode, or parse errors, or diagnostics from other tools.
- An agent may suggest an override and its justification, but must receive explicit manual approval from the user before adding or changing an override comment.
- Do not implement overrides automatically or use them as a substitute for investigating a finding.

## Agent handoff constraints

- Inspect existing behavior and tests before modifying a candidate.
- Preserve public APIs and observable behavior unless separately authorized.
- Treat these metrics as signals, not automatic proof of poor design.
- Apply separation of concerns and DRY without introducing needless abstractions.
- Run relevant tests and static checks after each coherent refactor.
