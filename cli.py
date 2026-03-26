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
        help="Çıktı formatı: csv | jsonl | parquet | txt (varsayılan: jsonl)",
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

    args = parser.parse_args()

    data_type = DataType(args.type)
    export_format = ExportFormat(args.format)

    if args.dry_run:
        from intent.parser import parse_intent
        import json, dataclasses
        spec = parse_intent(args.prompt, data_type=data_type, row_count=args.rows)
        print("\n=== DRY RUN — DataSpec ===")
        print(json.dumps(dataclasses.asdict(spec), ensure_ascii=False, indent=2))
        return

    from pipeline import run

    print(f"\n{'='*50}")
    print(f"SynthForge")
    print(f"{'='*50}")
    print(f"Prompt   : {args.prompt}")
    print(f"Tip      : {data_type.value}")
    print(f"Kayıt    : {args.rows}")
    print(f"Format   : {export_format.value}")
    print(f"{'='*50}\n")

    result = run(
        prompt=args.prompt,
        data_type=data_type,
        row_count=args.rows,
        export_format=export_format,
        output_dir=args.output,
        max_refine_iterations=args.max_refine,
        validate=not args.no_validate,
    )

    print(f"\n{'='*50}")
    print(f"✓ Tamamlandı")
    print(f"  Kayıt sayısı : {len(result.dataset.records)}")
    print(f"  Validation   : {'✓ Geçti' if result.validation.passed else '✗ Kısmi'} (score={result.validation.score})")
    print(f"  İterasyon    : {result.iterations}")
    print(f"  Dosya        : {result.export_path}")

    if result.validation.issues:
        print(f"\n  Kalan sorunlar ({len(result.validation.issues)}):")
        for issue in result.validation.issues[:5]:
            print(f"    • {issue}")

    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
