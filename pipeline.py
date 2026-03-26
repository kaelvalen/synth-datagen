from __future__ import annotations
from core.types import (
    DataType, DataSpec, ExportFormat, PipelineResult
)


def run(
    prompt: str,
    data_type: DataType,
    row_count: int = 100,
    export_format: ExportFormat = ExportFormat.JSONL,
    output_dir: str = "./output",
    max_refine_iterations: int = 3,
    validate: bool = True,
) -> PipelineResult:
    """
    Ana pipeline:
      prompt + tip → intent parse → generate → validate → refine loop → export
    """
    from intent.parser import parse_intent
    from validators.checker import validate as do_validate
    from refiners.refiner import refine
    from exporters.writer import export

    # 1. Intent → DataSpec
    print(f"\n[pipeline] Intent parse ediliyor...")
    spec = parse_intent(prompt, data_type=data_type, row_count=row_count)
    print(f"[pipeline] Spec: '{spec.name}' | {spec.row_count} kayıt | {len(spec.fields)} alan")

    # 2. Generate
    print(f"[pipeline] Veri üretiliyor ({spec.data_type.value})...")
    dataset = _generate(spec)
    print(f"[pipeline] {len(dataset.records)} kayıt üretildi.")

    # 3. Validate + Refine loop
    iterations = 0
    if validate:
        print(f"[pipeline] Validasyon başlıyor...")
        validation = do_validate(dataset)
        print(f"[pipeline] Validation score: {validation.score} | Geçti: {validation.passed}")

        if not validation.passed:
            dataset, iterations = refine(dataset, validation, max_iterations=max_refine_iterations)
            validation = do_validate(dataset)
            print(f"[pipeline] Final validation score: {validation.score}")
    else:
        from core.types import ValidationResult
        validation = ValidationResult(passed=True, score=1.0)

    # 4. Export
    path = export(dataset, fmt=export_format, output_dir=output_dir)

    return PipelineResult(
        dataset=dataset,
        validation=validation,
        iterations=iterations,
        export_path=path,
    )


def _generate(spec: DataSpec):
    from core.types import DataType
    from generators import tabular, nlp, timeseries, log

    dispatch = {
        DataType.TABULAR: tabular.generate,
        DataType.NLP: nlp.generate,
        DataType.TIMESERIES: timeseries.generate,
        DataType.LOG: log.generate,
    }
    generator = dispatch.get(spec.data_type)
    if not generator:
        raise ValueError(f"Desteklenmeyen data_type: {spec.data_type}")
    return generator(spec)
