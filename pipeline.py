from __future__ import annotations
import random
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
    seed: int | None = None,
    quiet: bool = False,
    compress: bool = False,
) -> PipelineResult:
    """
    Ana pipeline:
      prompt + tip → intent parse → generate → validate → refine loop → export
    
    Args:
        prompt: Doğal dil veri tanımı
        data_type: Veri tipi (tabular, nlp, timeseries, log)
        row_count: Üretilecek kayıt sayısı
        export_format: Çıktı formatı
        output_dir: Çıktı dizini
        max_refine_iterations: Maksimum refine döngüsü
        validate: Validation yapılsın mı
        seed: Reproducibility için random seed
        quiet: Sessiz mod
        compress: Çıktıyı sıkıştır
    """
    from intent.parser import parse_intent
    from validators.checker import validate as do_validate
    from refiners.refiner import refine
    from exporters.writer import export
    
    # Seed support
    if seed is not None:
        random.seed(seed)

    # Progress tracking
    try:
        from core.console import create_progress, get_logger, print_info, print_success, print_warning
        use_rich = not quiet
        logger = get_logger()
    except ImportError:
        use_rich = False
        import logging
        logger = logging.getLogger("synthforge")

    # 1. Intent → DataSpec
    if use_rich:
        print_info("Intent parse ediliyor...")
    
    spec = parse_intent(prompt, data_type=data_type, row_count=row_count)
    logger.debug(f"Spec: '{spec.name}' | {spec.row_count} kayıt | {len(spec.fields)} alan")

    # 2. Generate
    if use_rich:
        print_info(f"Veri üretiliyor ({spec.data_type.value})...")
    
    dataset = _generate(spec)
    logger.debug(f"{len(dataset.records)} kayıt üretildi.")

    # 3. Validate + Refine loop
    iterations = 0
    if validate:
        if use_rich:
            print_info("Validasyon başlıyor...")
        
        validation = do_validate(dataset)
        logger.debug(f"Validation score: {validation.score} | Geçti: {validation.passed}")

        if not validation.passed:
            if use_rich:
                print_warning(f"Sorunlar tespit edildi, refine ediliyor...")
            dataset, iterations = refine(dataset, validation, max_iterations=max_refine_iterations)
            validation = do_validate(dataset)
            logger.debug(f"Final validation score: {validation.score}")
    else:
        from core.types import ValidationResult
        validation = ValidationResult(passed=True, score=1.0)

    # 4. Export
    path = export(dataset, fmt=export_format, output_dir=output_dir, compress=compress)
    
    if use_rich:
        print_success(f"Dosya kaydedildi: {path}")

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
