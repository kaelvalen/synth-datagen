from __future__ import annotations
import json

from core.llm import chat_json
from core.types import DataSpec, GeneratedDataset, ValidationResult

REFINE_SYSTEM = """
Sen bir veri kalitesi iyileştirme uzmanısın.

Sana:
1. Veri seti spesifikasyonu
2. Mevcut kayıtlar (örnek)
3. Tespit edilen sorunlar ve öneriler

verilecek. Sorunları gidererek düzeltilmiş kayıtları döndür.

SADECE JSON array döndür — düzeltilmiş kayıtların TAM listesi.
Markdown veya açıklama ekleme.
"""


def refine(
    dataset: GeneratedDataset,
    validation: ValidationResult,
    max_iterations: int = 3,
) -> tuple[GeneratedDataset, int]:
    """
    Validate → Refine döngüsü.
    max_iterations kez dener; her seferinde sorunları LLM'e iletir.
    
    Returns:
        (refined_dataset, iteration_count)
    """
    from validators.checker import validate

    current = dataset
    iteration = 0

    for i in range(max_iterations):
        iteration = i + 1

        if validation.passed:
            print(f"[refiner] ✓ Iterasyon {iteration}: Validation geçti (score={validation.score})")
            break

        print(
            f"[refiner] Iterasyon {iteration}: {len(validation.issues)} sorun "
            f"(score={validation.score}) — refine ediliyor..."
        )

        refined = _llm_refine(current, validation)
        current = refined

        # Yeniden validate et
        validation = validate(current)

    return current, iteration


def _llm_refine(
    dataset: GeneratedDataset,
    validation: ValidationResult,
) -> GeneratedDataset:
    spec = dataset.spec

    # Büyük veri setlerinde sadece sorunlu kısmı gönder
    sample_size = min(30, len(dataset.records))
    sample = dataset.records[:sample_size]

    user_msg = f"""
Spesifikasyon:
{json.dumps({
    "name": spec.name,
    "data_type": spec.data_type,
    "context": spec.context,
    "constraints": spec.constraints,
    "fields": [
        {"name": f.name, "dtype": f.dtype, "categories": f.categories,
         "min_val": f.min_val, "max_val": f.max_val, "unique": f.unique,
         "nullable": f.nullable, "description": f.description}
        for f in spec.fields
    ],
}, ensure_ascii=False, indent=2)}

Tespit edilen sorunlar:
{json.dumps(validation.issues, ensure_ascii=False, indent=2)}

Öneriler:
{json.dumps(validation.suggestions, ensure_ascii=False, indent=2)}

Düzeltilecek kayıtlar ({sample_size} adet):
{json.dumps(sample, ensure_ascii=False, indent=2, default=str)}

Bu {sample_size} kaydı sorunları gidererek düzelt. JSON array döndür.
    """.strip()

    try:
        refined_records = chat_json(
            system=REFINE_SYSTEM,
            user=user_msg,
            temperature=0.3,
            max_tokens=4096,
        )

        if not isinstance(refined_records, list):
            print("[refiner] LLM beklenmedik format döndürdü, orijinal korunuyor.")
            return dataset

        # Sadece sample kısmını güncelle, geri kalanı koru
        updated_records = refined_records[:sample_size] + dataset.records[sample_size:]

        return GeneratedDataset(
            spec=dataset.spec,
            records=updated_records,
            metadata={**dataset.metadata, "refined": True},
        )

    except (ValueError, Exception) as e:
        print(f"[refiner] LLM refine başarısız: {e} — orijinal korunuyor.")
        return dataset
