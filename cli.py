#!/usr/bin/env python3
"""
SynthForge CLI
Kullanım:
  python cli.py --help
  python cli.py "e-ticaret sipariş verisi üret" --type tabular --rows 200 --format csv
  python cli.py "kullanıcı yorumları" --type nlp --rows 50 --format jsonl
  python cli.py "API erişim logları" --type log --rows 500 --format jsonl
  python cli.py "CPU ve bellek metrikleri" --type timeseries --rows 1000 --format csv
"""
import argparse
import sys
import os

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(__file__))

from core.types import DataType, ExportFormat


def main():
    parser = argparse.ArgumentParser(
        description="SynthForge — İsteğe göre kusursuz sentetik veri üretici",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("prompt", help="Veri setini tanımlayan doğal dil açıklaması")
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in DataType],
        required=True,
        help="Veri tipi: tabular | nlp | timeseries | log",
    )
    parser.add_argument(
        "--rows", "-r",
        type=int,
        default=100,
        help="Üretilecek kayıt sayısı (varsayılan: 100)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=[f.value for f in ExportFormat],
        default="jsonl",
        help="Çıktı formatı: csv | jsonl | parquet | txt | sql | xlsx (varsayılan: jsonl)",
    )
    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Çıktı dizini (varsayılan: ./output)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Validation + refine döngüsünü atla (daha hızlı)",
    )
    parser.add_argument(
        "--max-refine",
        type=int,
        default=3,
        help="Maksimum refine iterasyon sayısı (varsayılan: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sadece intent parse et, veri üretme (spec'i göster)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Reproducibility için random seed",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Sadece hata ve sonuç göster",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Detaylı çıktı göster",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="YAML config dosyası",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Çıktıyı gzip ile sıkıştır",
    )

    args = parser.parse_args()

    # Logging setup
    from core.console import setup_logging, console, print_header, print_success, print_error
    from core.console import print_spec_table, print_fields_table, print_result_summary
    
    log_level = "WARNING" if args.quiet else ("DEBUG" if args.verbose else "INFO")
    logger = setup_logging(level=log_level)

    # Config file support
    if args.config:
        args = _merge_config(args)

    # Seed support
    if args.seed is not None:
        import random
        random.seed(args.seed)
        try:
            import numpy as np
            np.random.seed(args.seed)
        except ImportError:
            pass

    data_type = DataType(args.type)
    export_format = ExportFormat(args.format)

    if args.dry_run:
        from intent.parser import parse_intent
        from core.console import create_spinner_progress
        
        with create_spinner_progress() as progress:
            task = progress.add_task("Intent parse ediliyor...", total=None)
            spec = parse_intent(args.prompt, data_type=data_type, row_count=args.rows)
        
        print_spec_table(spec)
        print_fields_table(spec.fields)
        return

    from pipeline import run
    from core.console import create_progress

    if not args.quiet:
        print_header("SynthForge", "Sentetik veri üretici")
        console.print(f"[dim]Prompt:[/dim] {args.prompt}")
        console.print(f"[dim]Type:[/dim] {data_type.value} | [dim]Rows:[/dim] {args.rows} | [dim]Format:[/dim] {export_format.value}")
        console.print()

    try:
        result = run(
            prompt=args.prompt,
            data_type=data_type,
            row_count=args.rows,
            export_format=export_format,
            output_dir=args.output,
            max_refine_iterations=args.max_refine,
            validate=not args.no_validate,
            seed=args.seed,
            quiet=args.quiet,
            compress=args.compress,
        )

        if not args.quiet:
            print_result_summary(result)
        else:
            console.print(f"✓ {result.export_path}")

    except KeyboardInterrupt:
        print_error("İptal edildi.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Hata: {e}")
        if args.verbose:
            console.print_exception()
        sys.exit(1)


def _merge_config(args):
    """Merge config file with CLI args."""
    import yaml
    
    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
        
        # CLI args override config
        for key, value in config.items():
            if hasattr(args, key) and getattr(args, key) is None:
                setattr(args, key, value)
    except Exception as e:
        from core.console import print_warning
        print_warning(f"Config dosyası okunamadı: {e}")
    
    return args


if __name__ == "__main__":
    main()
