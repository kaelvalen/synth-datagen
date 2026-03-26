from __future__ import annotations
import json
import random

from core.llm import chat_json
from core.types import DataSpec, GeneratedDataset

SYSTEM_PROMPT = """
Sen bir sentetik veri üreticisisin. Verilen spesifikasyona göre gerçekçi, çeşitli ve bağlamlı metin kayıtları üret.

SADECE JSON array döndür. Her eleman spec'teki field'ları içeren bir nesne olmalı.
Markdown veya açıklama ekleme. Sadece JSON.

Önemli:
- Her kayıt birbirinden farklı olmalı.
- Domain bağlamına uygun ol.
- Gerçekçi dil kullan — kalıp ifadelerden kaçın.
"""


def generate(spec: DataSpec) -> GeneratedDataset:
    """NLP veri setini batch'ler halinde LLM ile üretir."""
    batch_size = 10
    all_records = []

    fields_desc = json.dumps(
        [{"name": f.name, "dtype": f.dtype, "description": f.description} for f in spec.fields],
        ensure_ascii=False,
        indent=2,
    )

    total_batches = (spec.row_count + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        remaining = spec.row_count - len(all_records)
        current_batch = min(batch_size, remaining)

        user_msg = f"""
Veri seti adı: {spec.name}
Bağlam: {spec.context}
Üretilecek kayıt sayısı: {current_batch}
Locale: {spec.locale}

Alanlar:
{fields_desc}

Kısıtlamalar: {spec.constraints}

{current_batch} adet kayıt üret. JSON array formatında döndür.
        """.strip()

        try:
            batch = chat_json(
                system=SYSTEM_PROMPT,
                user=user_msg,
                max_tokens=2048,
                temperature=0.8,
            )
            if isinstance(batch, list):
                all_records.extend(batch[:current_batch])
            else:
                # LLM dict döndürdüyse "data" key'ini dene
                if "data" in batch:
                    all_records.extend(batch["data"][:current_batch])
        except (ValueError, KeyError) as e:
            print(f"[nlp_generator] Batch {batch_idx + 1} başarısız: {e} — atlanıyor.")

        print(f"[nlp_generator] {len(all_records)}/{spec.row_count} kayıt üretildi.")

    return GeneratedDataset(
        spec=spec,
        records=all_records[: spec.row_count],
        metadata={"generator": "nlp", "batches": total_batches},
    )
