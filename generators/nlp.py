from __future__ import annotations
import json
import random

from core.llm import chat_json
from core.types import DataSpec, GeneratedDataset

SYSTEM_PROMPT = """
Sen uzman bir sentetik veri üreticisisin. Verilen spesifikasyona göre SON DERECE GERÇEKÇİ, çeşitli ve tutarlı metin kayıtları üretiyorsun.

KRİTİK KURALLAR:
1. Her kayıt BİRBİRİNDEN FARKLI ve özgün olmalı
2. Gerçek dünya verisini taklit et - kalıp ifadelerden kaçın
3. Domain terminolojisini doğru kullan
4. Sentiment/duygu ile içerik tutarlı olmalı (pozitif → olumlu kelimeler)
5. Yazım hataları, kısaltmalar, emoji kullanımı gerçekçi olabilir
6. Locale'e uygun dil ve ifadeler kullan

METİN KALİTESİ:
- Ürün yorumu → gerçek kullanıcı gibi yaz, artı/eksi belirt
- Destek talebi → somut problem tanımla, detay ver
- Sosyal medya → informal, emoji, hashtag olabilir
- Profesyonel → formal dil, teknik terimler

SADECE JSON array döndür. Her eleman spec'teki field'ları içeren bir nesne olmalı.
Markdown veya açıklama ekleme. Sadece JSON.
"""


def generate(spec: DataSpec) -> GeneratedDataset:
    """NLP veri setini batch'ler halinde LLM ile üretir."""
    batch_size = 15  # Daha büyük batch'ler daha tutarlı sonuç verir
    all_records = []

    fields_desc = json.dumps(
        [
            {
                "name": f.name, 
                "dtype": f.dtype, 
                "description": f.description,
                "categories": f.categories if f.categories else None,
                "min_val": f.min_val,
                "max_val": f.max_val,
            } 
            for f in spec.fields
        ],
        ensure_ascii=False,
        indent=2,
    )

    total_batches = (spec.row_count + batch_size - 1) // batch_size
    
    # Varyasyon için farklı senaryolar
    scenarios = _generate_scenarios(spec)

    for batch_idx in range(total_batches):
        remaining = spec.row_count - len(all_records)
        current_batch = min(batch_size, remaining)
        
        # Her batch için farklı senaryo ipuçları
        scenario_hint = scenarios[batch_idx % len(scenarios)] if scenarios else ""

        user_msg = f"""
Veri seti: {spec.name}
Bağlam: {spec.context}
Üretilecek kayıt sayısı: {current_batch}
Locale: {spec.locale}

Alanlar:
{fields_desc}

Kısıtlamalar: {spec.constraints}

{scenario_hint}

ÖNEMLİ:
- Her kayıt benzersiz ve farklı olmalı
- Gerçek kullanıcılar gibi doğal dil kullan
- Rating ile yorum içeriği tutarlı olmalı (düşük rating → olumsuz yorum)
- Çeşitli uzunluklarda içerik üret (kısa, orta, uzun)

{current_batch} adet kayıt üret. JSON array formatında döndür.
        """.strip()

        try:
            batch = chat_json(
                system=SYSTEM_PROMPT,
                user=user_msg,
                max_tokens=4096,
                temperature=0.85,  # Daha yaratıcı
            )
            if isinstance(batch, list):
                all_records.extend(batch[:current_batch])
            else:
                if "data" in batch:
                    all_records.extend(batch["data"][:current_batch])
        except (ValueError, KeyError) as e:
            print(f"[nlp_generator] Batch {batch_idx + 1} başarısız: {e} — tekrar deneniyor...")
            # Retry with lower temperature
            try:
                batch = chat_json(
                    system=SYSTEM_PROMPT,
                    user=user_msg,
                    max_tokens=4096,
                    temperature=0.5,
                )
                if isinstance(batch, list):
                    all_records.extend(batch[:current_batch])
            except Exception:
                pass

        print(f"[nlp_generator] {len(all_records)}/{spec.row_count} kayıt üretildi.")

    return GeneratedDataset(
        spec=spec,
        records=all_records[: spec.row_count],
        metadata={"generator": "nlp", "batches": total_batches},
    )


def _generate_scenarios(spec: DataSpec) -> list[str]:
    """Veri çeşitliliği için farklı senaryolar üret."""
    context = spec.context.lower()
    
    if "yorum" in context or "review" in context:
        return [
            "Bu batch'te: Çoğunlukla memnun müşteriler, detaylı pozitif yorumlar.",
            "Bu batch'te: Karışık deneyimler, hem olumlu hem olumsuz yönler.",
            "Bu batch'te: Hayal kırıklığına uğramış müşteriler, somut şikayetler.",
            "Bu batch'te: Kısa ve öz yorumlar, hızlı değerlendirmeler.",
            "Bu batch'te: Uzun detaylı incelemeler, karşılaştırmalar.",
        ]
    
    if "destek" in context or "ticket" in context or "support" in context:
        return [
            "Bu batch'te: Teknik sorunlar, hata mesajları, sistem problemleri.",
            "Bu batch'te: Fatura ve ödeme soruları, hesap problemleri.",
            "Bu batch'te: Ürün kullanımı, nasıl yapılır soruları.",
            "Bu batch'te: Şikayetler ve iade talepleri.",
            "Bu batch'te: Genel sorular ve bilgi talepleri.",
        ]
    
    if "sosyal" in context or "social" in context or "tweet" in context:
        return [
            "Bu batch'te: Olumlu paylaşımlar, övgüler, öneriler.",
            "Bu batch'te: Şikayetler, eleştiriler, hayal kırıklıkları.",
            "Bu batch'te: Sorular, yardım talepleri.",
            "Bu batch'te: Haberler, duyurular üzerine yorumlar.",
        ]
    
    return [
        "Bu batch'te çeşitli ve dengeli içerikler üret.",
        "Bu batch'te farklı bakış açıları ve tonlar kullan.",
    ]
