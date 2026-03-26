from __future__ import annotations
import json
from core.llm import chat_json
from core.types import DataSpec, DataType, FieldSpec

SYSTEM_PROMPT = """
Sen uzman bir veri mühendisisin. Kullanıcının doğal dil açıklamasını analiz ederek profesyonel bir veri seti spesifikasyonu oluşturuyorsun.

GÖREVIN:
1. Kullanıcının ihtiyacını anla
2. Domain'e uygun, gerçekçi alanlar tasarla
3. Akıllı varsayılan değerler belirle
4. Cross-field ilişkileri tespit et

SADECE geçerli JSON döndür. Markdown ya da açıklama ekleme.

JSON FORMATI:
{
  "name": "dataset_adı (snake_case)",
  "data_type": "tabular | nlp | timeseries | log",
  "row_count": <integer>,
  "locale": "en_US veya tr_TR gibi",
  "context": "domain hakkında detaylı notlar - generator'a rehberlik edecek",
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
      "description": "alanın amacı ve içeriği hakkında detaylı açıklama"
    }
  ]
}

KURALLAR:
1. ALAN İSİMLERİ:
   - snake_case kullan (customer_name, order_date)
   - Anlamlı ve açıklayıcı isimler seç
   - ID alanları için _id suffix kullan

2. VERİ TİPLERİ:
   - Para: float, min=0.01, max contextual
   - Yaş: int, min=0 veya 18, max=120
   - Yüzde: float, min=0, max=100
   - Tarih: datetime, gerçekçi min/max range
   - Durum: category, tüm olası değerleri listele

3. CATEGORIES:
   - Her category alanı için EN AZ 4-5 değer belirt
   - Gerçekçi ve domain'e uygun değerler seç
   - Türkçe context ise Türkçe değerler kullanılabilir

4. CONSTRAINTS:
   - Tarih ilişkileri: "end_date > start_date"
   - Sayısal: "total = quantity * unit_price"
   - Mantıksal: "is_paid = true when status = 'delivered'"

5. CONTEXT:
   - Generator'a yol gösterecek detaylı bilgi ver
   - Domain terminolojisini açıkla
   - Veri dağılımı hakkında ipuçları ver (örn: "çoğu sipariş tamamlanmış olmalı")

6. LOCALE:
   - Türkçe prompt → tr_TR
   - İngilizce prompt → en_US
   - Locale'e göre isimler, adresler uygun üretilecek

ÖRNEK - İyi bir field tanımı:
{
  "name": "order_status",
  "dtype": "category",
  "nullable": false,
  "unique": false,
  "categories": ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "returned"],
  "description": "Sipariş durumu. Çoğunlukla delivered ve shipped olmalı, cancelled ve returned nadir."
}
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

    raw = chat_json(system=SYSTEM_PROMPT, user=user_msg, temperature=0.3)
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
