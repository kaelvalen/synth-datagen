from __future__ import annotations
import json
from core.llm import chat_json
from core.types import DataSpec, DataType, FieldSpec

SYSTEM_PROMPT = """
Sen bir veri mühendisisin. Kullanıcının doğal dil açıklamasını, bir veri seti spesifikasyonuna dönüştürüyorsun.

SADECE geçerli JSON döndür. Markdown ya da açıklama ekleme.

Döndürmen gereken JSON formatı:
{
  "name": "dataset_adı (snake_case)",
  "data_type": "tabular | nlp | timeseries | log",
  "row_count": <integer>,
  "locale": "en_US veya tr_TR gibi",
  "context": "domain hakkında kısa notlar",
  "constraints": ["cross-field kısıt1", "kısıt2"],
  "fields": [
    {
      "name": "alan_adı",
      "dtype": "int | float | str | bool | datetime | category",
      "nullable": false,
      "unique": false,
      "min_val": null,
      "max_val": null,
      "categories": [],
      "pattern": null,
      "foreign_key": null,
      "description": "ne anlama geldiği"
    }
  ]
}

Kurallar:
- row_count belirtilmemişse 100 kullan.
- ID alanları unique:true olmalı.
- Kategorik alanlar için categories listesi dolu olmalı (en az 3 örnek değer).
- datetime için min_val/max_val ISO 8601 string olabilir.
- constraints: ör. "age >= 18 when is_adult=true", "end_time > start_time"
- data_type seçimi: tablo → tabular, metin/yorum → nlp, sensör/metrik → timeseries, sistem eventi → log
"""


def parse_intent(
    prompt: str,
    data_type: DataType | None = None,
    row_count: int | None = None,
) -> DataSpec:
    """
    Kullanıcı prompt'unu DataSpec'e parse eder.

    Args:
        prompt: Doğal dil açıklaması.
        data_type: Kullanıcı UI'dan seçtiyse override et.
        row_count: Kullanıcı belirtmişse override et.
    """
    override_hints = []
    if data_type:
        override_hints.append(f"data_type MUTLAKA '{data_type.value}' olsun.")
    if row_count:
        override_hints.append(f"row_count MUTLAKA {row_count} olsun.")

    user_msg = prompt
    if override_hints:
        user_msg += "\n\nEk kısıtlar:\n" + "\n".join(override_hints)

    raw = chat_json(system=SYSTEM_PROMPT, user=user_msg, temperature=0.2)
    return _raw_to_spec(raw)


def _raw_to_spec(raw: dict) -> DataSpec:
    fields = [
        FieldSpec(
            name=f["name"],
            dtype=f["dtype"],
            nullable=f.get("nullable", False),
            unique=f.get("unique", False),
            min_val=f.get("min_val"),
            max_val=f.get("max_val"),
            categories=f.get("categories", []),
            pattern=f.get("pattern"),
            foreign_key=f.get("foreign_key"),
            description=f.get("description", ""),
        )
        for f in raw["fields"]
    ]

    return DataSpec(
        data_type=DataType(raw["data_type"]),
        name=raw["name"],
        row_count=raw.get("row_count", 100),
        fields=fields,
        constraints=raw.get("constraints", []),
        context=raw.get("context", ""),
        locale=raw.get("locale", "en_US"),
    )
