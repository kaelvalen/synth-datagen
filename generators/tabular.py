from __future__ import annotations
import random
import re
import math
import string
from datetime import datetime, timedelta
from typing import Any

from faker import Faker
import rstr  # Regex'ten string üretimi için

from core.types import DataSpec, FieldSpec, GeneratedDataset

_faker_cache: dict[str, Faker] = {}


def _get_faker(locale: str) -> Faker:
    if locale not in _faker_cache:
        _faker_cache[locale] = Faker(locale)
        Faker.seed(random.randint(0, 999999))  # Daha fazla çeşitlilik
    return _faker_cache[locale]


def _generate_from_pattern(pattern: str, faker: Faker) -> str:
    """Regex pattern'dan gerçek değer üret."""
    if not pattern:
        return faker.word()
    
    # Özel pattern kısayolları
    shortcuts = {
        r"CUST[0-9]{5}": lambda: f"CUST{random.randint(10000, 99999)}",
        r"ORD[0-9]{6}": lambda: f"ORD{random.randint(100000, 999999)}",
        r"ORD-[0-9]{6}": lambda: f"ORD-{random.randint(100000, 999999)}",
        r"INV[0-9]{8}": lambda: f"INV{random.randint(10000000, 99999999)}",
        r"SKU-[A-Z]{2}-[0-9]{4}": lambda: f"SKU-{''.join(random.choices(string.ascii_uppercase, k=2))}-{random.randint(1000, 9999)}",
        r"PRD[0-9]{4}": lambda: f"PRD{random.randint(1000, 9999)}",
        r"TXN[0-9]{10}": lambda: f"TXN{random.randint(1000000000, 9999999999)}",
    }
    
    # Normalize pattern for matching
    norm = pattern.replace("\\d", "[0-9]").replace("\\w", "[A-Za-z0-9]")
    
    for pat, gen in shortcuts.items():
        if pat in norm or pattern == pat:
            return gen()
    
    # rstr ile regex'ten üret
    try:
        # Basit pattern'ları rstr ile üret
        return rstr.xeger(pattern)
    except Exception:
        pass
    
    # Faker bothify fallback - ? = harf, # = rakam
    bothify_pattern = pattern
    bothify_pattern = re.sub(r'\[0-9\]\{(\d+)\}', lambda m: '#' * int(m.group(1)), bothify_pattern)
    bothify_pattern = re.sub(r'\[A-Z\]\{(\d+)\}', lambda m: '?' * int(m.group(1)), bothify_pattern)
    bothify_pattern = re.sub(r'\\d', '#', bothify_pattern)
    bothify_pattern = re.sub(r'\\w', '?', bothify_pattern)
    
    return faker.bothify(text=bothify_pattern)


# ── Gerçekçi Dağılımlar ─────────────────────────────────────────────────────

def _realistic_int(lo: int, hi: int, distribution: str = "normal") -> int:
    """Gerçekçi dağılımlı integer üret."""
    if distribution == "normal":
        # Çoğu değer ortada yoğunlaşır
        mean = (lo + hi) / 2
        std = (hi - lo) / 4
        val = random.gauss(mean, std)
        return int(max(lo, min(hi, val)))
    elif distribution == "exponential":
        # Küçük değerler daha olası (örn: sipariş miktarı)
        scale = (hi - lo) / 3
        val = lo + random.expovariate(1 / scale)
        return int(max(lo, min(hi, val)))
    elif distribution == "bimodal":
        # İki tepe noktası (örn: yaş - genç ve orta yaşlı)
        if random.random() < 0.5:
            val = random.gauss(lo + (hi - lo) * 0.25, (hi - lo) * 0.1)
        else:
            val = random.gauss(lo + (hi - lo) * 0.7, (hi - lo) * 0.1)
        return int(max(lo, min(hi, val)))
    return random.randint(lo, hi)


def _realistic_float(lo: float, hi: float, name: str = "") -> float:
    """Gerçekçi float üret."""
    name_lower = name.lower()
    
    # Fiyat: .99, .95, .00 ile biten değerler daha gerçekçi
    if any(k in name_lower for k in ("price", "fiyat", "amount", "tutar", "cost", "maliyet")):
        base = random.uniform(lo, hi)
        endings = [0.99, 0.95, 0.00, 0.49, 0.50]
        ending = random.choice(endings)
        return round(int(base) + ending, 2)
    
    # Yüzde: 0-100 arası, belirli değerler daha olası
    if any(k in name_lower for k in ("percent", "rate", "oran", "ratio")):
        common_values = [0, 5, 10, 15, 20, 25, 30, 50, 75, 90, 95, 100]
        if random.random() < 0.3:
            return float(random.choice([v for v in common_values if lo <= v <= hi]))
        return round(random.uniform(lo, hi), 1)
    
    # Rating: Genellikle yüksek (3.5-5 arası daha olası)
    if any(k in name_lower for k in ("rating", "score", "puan")):
        # Çoğu rating 3.5-5 arası
        if random.random() < 0.7:
            return round(random.uniform(max(lo, 3.5), hi), 1)
        return round(random.uniform(lo, hi), 1)
    
    return round(random.uniform(lo, hi), 2)


def _realistic_category(categories: list[str], description: str = "") -> str:
    """Description'a göre ağırlıklı kategori seç."""
    desc_lower = description.lower()
    
    # "çoğunlukla", "genellikle", "nadir" gibi ipuçlarına bak
    weights = [1.0] * len(categories)
    
    for i, cat in enumerate(categories):
        cat_lower = cat.lower()
        # Olumlu durumlar genellikle daha sık
        if cat_lower in ("delivered", "completed", "success", "active", "approved", "tamamlandı"):
            weights[i] = 3.0
        elif cat_lower in ("shipped", "processing", "in_progress", "pending"):
            weights[i] = 2.0
        elif cat_lower in ("cancelled", "failed", "rejected", "inactive", "iptal"):
            weights[i] = 0.5
        elif cat_lower in ("returned", "refunded", "iade"):
            weights[i] = 0.3
    
    return random.choices(categories, weights=weights)[0]


# ── Alan üreticileri ────────────────────────────────────────────────────────

def _generate_field_value(field: FieldSpec, faker: Faker, row_idx: int, context: dict = None) -> Any:
    dtype = field.dtype
    name_lower = field.name.lower()
    context = context or {}

    # Nullable kontrolü - daha gerçekçi oranlar
    if field.nullable:
        null_rate = 0.05  # Varsayılan %5
        # Bazı alanlar daha sık null olabilir
        if any(k in name_lower for k in ("optional", "secondary", "middle", "suffix")):
            null_rate = 0.15
        if random.random() < null_rate:
            return None

    # Pattern varsa önce pattern'dan üret (str tipi için)
    if dtype == "str" and field.pattern:
        return _generate_from_pattern(field.pattern, faker)

    # Semantik isim eşleştirme
    if dtype == "str":
        val = _semantic_str(name_lower, faker, field.description)
        if val is not None:
            return val

    if dtype == "int":
        lo = int(field.min_val) if field.min_val is not None else 0
        hi = int(field.max_val) if field.max_val is not None else 10_000
        
        # Alan tipine göre dağılım seç
        if any(k in name_lower for k in ("quantity", "miktar", "count", "adet")):
            return _realistic_int(lo, hi, "exponential")
        elif any(k in name_lower for k in ("age", "yas")):
            return _realistic_int(lo, hi, "bimodal")
        return _realistic_int(lo, hi, "normal")

    if dtype == "float":
        lo = float(field.min_val) if field.min_val is not None else 0.0
        hi = float(field.max_val) if field.max_val is not None else 1000.0
        return _realistic_float(lo, hi, field.name)

    if dtype == "bool":
        # Bazı boolean'lar daha sık True olur
        true_rate = 0.5
        if any(k in name_lower for k in ("is_active", "enabled", "verified", "available")):
            true_rate = 0.85
        elif any(k in name_lower for k in ("is_deleted", "is_spam", "is_blocked")):
            true_rate = 0.1
        return random.random() < true_rate

    if dtype == "category":
        if field.categories:
            return _realistic_category(field.categories, field.description)
        return faker.word()

    if dtype == "datetime":
        lo_str = field.min_val or "2020-01-01T00:00:00"
        hi_str = field.max_val or "2025-12-31T23:59:59"
        try:
            lo_dt = datetime.fromisoformat(lo_str)
            hi_dt = datetime.fromisoformat(hi_str)
        except ValueError:
            lo_dt = datetime(2020, 1, 1)
            hi_dt = datetime(2025, 12, 31)
        
        delta = hi_dt - lo_dt
        
        # Daha gerçekçi zaman dağılımı - son zamanlara yakın tarihler daha olası
        if any(k in name_lower for k in ("created", "registered", "joined")):
            # Exponential - son zamanlara yakın
            rand_ratio = 1 - math.sqrt(random.random())  # Son tarihlere ağırlık
            rand_sec = int(delta.total_seconds() * rand_ratio)
        else:
            rand_sec = random.randint(0, int(delta.total_seconds()))
        
        return (lo_dt + timedelta(seconds=rand_sec)).isoformat()

    if dtype == "str":
        # Fallback for str without pattern or semantic match
        return faker.sentence(nb_words=4)

    return None


def _semantic_str(name: str, faker: Faker, description: str = "") -> str | None:
    """Alan ismine göre anlamlı faker değeri seç.
    
    ÖNEMLİ: Eşleştirme sırası önemli! Daha spesifik pattern'lar önce kontrol edilir.
    """
    desc_lower = description.lower()
    
    # Önce tam eşleşme veya spesifik composite isimler (product_name != name)
    exact_mappings = {
        # Ürün isimleri - KİŞİ İSMİ DEĞİL
        "product_name": lambda: faker.catch_phrase(),
        "product_title": lambda: faker.catch_phrase(),
        "item_name": lambda: faker.catch_phrase(),
        
        # Kişi isimleri - sadece tam eşleşme
        "customer_name": faker.name,
        "user_name": faker.user_name,  # username, not name
        "full_name": faker.name,
        "first_name": faker.first_name,
        "last_name": faker.last_name,
        
        # ID'ler
        "customer_id": lambda: f"CUST{random.randint(10000, 99999)}",
        "order_id": lambda: f"ORD{random.randint(100000, 999999)}",
        "product_id": lambda: f"PRD{random.randint(1000, 9999)}",
        "transaction_id": lambda: f"TXN{random.randint(1000000000, 9999999999)}",
        "invoice_id": lambda: f"INV{random.randint(10000000, 99999999)}",
        
        # E-ticaret spesifik
        "sku": lambda: f"SKU-{''.join(random.choices(string.ascii_uppercase, k=2))}-{random.randint(1000, 9999)}",
        "tracking_number": lambda: f"TRK{random.randint(100000000000, 999999999999)}",
        "coupon_code": lambda: ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
    }
    
    # Tam eşleşme kontrolü
    if name in exact_mappings:
        return exact_mappings[name]()
    
    # Description'a dayalı akıllı eşleştirme
    if "product" in desc_lower or "ürün" in desc_lower:
        if "name" in name or "title" in name:
            return faker.catch_phrase()
    
    if "customer" in desc_lower or "müşteri" in desc_lower:
        if "name" in name:
            return faker.name()
    
    # Suffix bazlı eşleştirme (daha güvenli)
    suffix_mappings = {
        "_email": faker.email,
        "_phone": faker.phone_number,
        "_address": faker.address,
        "_city": faker.city,
        "_country": faker.country,
        "_company": faker.company,
        "_url": faker.url,
        "_ip": faker.ipv4,
    }
    
    for suffix, fn in suffix_mappings.items():
        if name.endswith(suffix):
            return fn()
    
    # Genel keyword mapping - ama sadece keyword tam kelime olarak geçiyorsa
    general_mappings = {
        "email": faker.email,
        "phone": faker.phone_number,
        "address": faker.address,
        "city": faker.city,
        "country": faker.country,
        "company": faker.company,
        "job": faker.job,
        "url": faker.url,
        "description": faker.paragraph,
        "comment": faker.paragraph,
        "bio": faker.text,
    }
    
    for key, fn in general_mappings.items():
        # Tam kelime eşleşmesi (word boundary)
        if re.search(rf'\b{key}\b', name) or name == key:
            return fn()
    
    return None


# ── Unique değer takibi ─────────────────────────────────────────────────────

def _generate_unique_values(field: FieldSpec, faker: Faker, count: int) -> list[Any]:
    seen: set = set()
    values: list[Any] = []
    max_attempts = count * 20
    attempts = 0
    while len(values) < count and attempts < max_attempts:
        v = _generate_field_value(field, faker, len(values))
        if v not in seen:
            seen.add(v)
            values.append(v)
        attempts += 1
    # Fallback: yeterli unique değer üretilemezse index ekle
    while len(values) < count:
        values.append(f"{field.name}_{len(values)}")
    return values


# ── Ana generator ───────────────────────────────────────────────────────────

def generate(spec: DataSpec) -> GeneratedDataset:
    faker = _get_faker(spec.locale)
    records: list[dict[str, Any]] = []

    # Unique alanlar için önce tam listeyi üret
    unique_pools: dict[str, list[Any]] = {}
    for field in spec.fields:
        if field.unique:
            unique_pools[field.name] = _generate_unique_values(field, faker, spec.row_count)

    for i in range(spec.row_count):
        row: dict[str, Any] = {}
        for field in spec.fields:
            if field.unique:
                row[field.name] = unique_pools[field.name][i]
            else:
                row[field.name] = _generate_field_value(field, faker, i)
        records.append(row)

    # Cross-field constraint uygulaması
    records = _apply_constraints(records, spec.constraints, spec.fields)

    return GeneratedDataset(
        spec=spec,
        records=records,
        metadata={"generator": "tabular", "locale": spec.locale},
    )


def _apply_constraints(
    records: list[dict], constraints: list[str], fields: list[FieldSpec]
) -> list[dict]:
    """
    Kapsamlı constraint enforcement:
    - Tarih ilişkileri: delivery_date > order_date
    - Matematiksel: total = quantity * unit_price
    - Mantıksal: cancelled => payment != completed
    """
    # Field isimlerinden tip haritası
    field_types = {f.name: f.dtype for f in fields}
    field_cats = {f.name: f.categories for f in fields}
    
    for record in records:
        # 1. Otomatik computed field tespiti ve düzeltme
        _fix_computed_fields(record, field_types)
        
        # 2. Tarih tutarlılığı
        _fix_date_ordering(record, field_types)
        
        # 3. Business logic tutarlılığı  
        _fix_business_logic(record, field_cats)
    
    # 4. Explicit constraint'leri uygula
    for constraint in constraints:
        for record in records:
            _apply_single_constraint(record, constraint, field_types)
    
    return records


def _fix_computed_fields(record: dict, field_types: dict) -> None:
    """Matematiksel ilişkileri düzelt: total = qty * price"""
    # total_amount, total_price, subtotal gibi alanları tespit et
    total_fields = [k for k in record.keys() if any(t in k.lower() for t in ('total', 'subtotal', 'amount')) 
                    and field_types.get(k) in ('float', 'int')]
    
    qty_fields = [k for k in record.keys() if any(q in k.lower() for q in ('quantity', 'qty', 'count', 'miktar', 'adet'))
                  and field_types.get(k) in ('int', 'float')]
    
    price_fields = [k for k in record.keys() if any(p in k.lower() for p in ('price', 'unit_price', 'fiyat', 'birim'))
                    and field_types.get(k) in ('float', 'int')
                    and not any(t in k.lower() for t in ('total', 'subtotal'))]
    
    # Eğer qty ve price varsa, total'i hesapla
    if total_fields and qty_fields and price_fields:
        qty = record.get(qty_fields[0], 1)
        price = record.get(price_fields[0], 0)
        
        if qty is not None and price is not None:
            try:
                calculated = float(qty) * float(price)
                # Discount varsa uygula
                discount_fields = [k for k in record.keys() if 'discount' in k.lower() and field_types.get(k) in ('float', 'int')]
                if discount_fields:
                    discount = record.get(discount_fields[0])
                    if discount is not None and discount != '':
                        calculated = calculated - float(discount)
                
                record[total_fields[0]] = round(calculated, 2)
            except (TypeError, ValueError):
                pass


def _fix_date_ordering(record: dict, field_types: dict) -> None:
    """Tarih sıralamasını düzelt."""
    date_fields = {k: v for k, v in record.items() if field_types.get(k) == 'datetime' and v}
    
    # Bilinen tarih çiftleri
    date_pairs = [
        ('order_date', 'delivery_date'),
        ('order_date', 'ship_date'),
        ('ship_date', 'delivery_date'),
        ('start_date', 'end_date'),
        ('created_at', 'updated_at'),
        ('created_at', 'completed_at'),
        ('birth_date', 'registration_date'),
        ('siparis_tarihi', 'teslimat_tarihi'),
    ]
    
    for earlier, later in date_pairs:
        if earlier in record and later in record:
            try:
                early_dt = datetime.fromisoformat(str(record[earlier]))
                late_dt = datetime.fromisoformat(str(record[later]))
                
                if late_dt <= early_dt:
                    # Later tarihi düzelt: 1-14 gün sonra
                    days_offset = random.randint(1, 14)
                    hours_offset = random.randint(0, 23)
                    record[later] = (early_dt + timedelta(days=days_offset, hours=hours_offset)).isoformat()
            except (ValueError, TypeError):
                pass


def _fix_business_logic(record: dict, field_cats: dict) -> None:
    """Business logic tutarlılığını sağla."""
    
    # Order status vs payment status uyumu
    order_status = None
    payment_status = None
    
    for key in record:
        key_lower = key.lower()
        if 'order' in key_lower and 'status' in key_lower:
            order_status = (key, str(record[key]).lower() if record[key] else None)
        elif 'payment' in key_lower and 'status' in key_lower:
            payment_status = (key, str(record[key]).lower() if record[key] else None)
    
    if order_status and payment_status:
        o_key, o_val = order_status
        p_key, p_val = payment_status
        
        # İptal edilmiş sipariş için ödeme completed olamaz
        if o_val in ('cancelled', 'canceled', 'iptal'):
            if p_val in ('completed', 'paid', 'success', 'tamamlandi'):
                # Payment'ı uygun bir değere çevir
                p_cats = field_cats.get(p_key, [])
                refund_opts = [c for c in p_cats if c.lower() in ('refunded', 'cancelled', 'failed', 'iade')]
                if refund_opts:
                    record[p_key] = random.choice(refund_opts)
                else:
                    record[p_key] = 'refunded'
        
        # Tamamlanmış sipariş için ödeme pending olamaz
        if o_val in ('delivered', 'completed', 'teslim'):
            if p_val in ('pending', 'beklemede', 'awaiting'):
                p_cats = field_cats.get(p_key, [])
                paid_opts = [c for c in p_cats if c.lower() in ('completed', 'paid', 'success')]
                if paid_opts:
                    record[p_key] = random.choice(paid_opts)
                else:
                    record[p_key] = 'completed'


def _apply_single_constraint(record: dict, constraint: str, field_types: dict) -> None:
    """Tek bir constraint'i uygula."""
    constraint = constraint.strip()
    
    # Tarih karşılaştırması: field_a > field_b
    match = re.match(r"(\w+)\s*>\s*(\w+)", constraint)
    if match:
        bigger, smaller = match.group(1), match.group(2)
        if bigger in record and smaller in record:
            try:
                if field_types.get(bigger) == 'datetime':
                    b = datetime.fromisoformat(str(record[bigger]))
                    s = datetime.fromisoformat(str(record[smaller]))
                    if b <= s:
                        record[bigger] = (s + timedelta(hours=random.randint(1, 72))).isoformat()
                else:
                    # Sayısal karşılaştırma
                    if float(record[bigger]) <= float(record[smaller]):
                        record[bigger] = float(record[smaller]) * random.uniform(1.01, 1.5)
            except (ValueError, TypeError):
                pass
    
    # Matematiksel: total = quantity * unit_price
    match = re.match(r"(\w+)\s*=\s*(\w+)\s*\*\s*(\w+)", constraint)
    if match:
        result, op1, op2 = match.group(1), match.group(2), match.group(3)
        if result in record and op1 in record and op2 in record:
            try:
                val1 = float(record[op1]) if record[op1] is not None else 0
                val2 = float(record[op2]) if record[op2] is not None else 0
                record[result] = round(val1 * val2, 2)
            except (ValueError, TypeError):
                pass
