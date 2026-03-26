from __future__ import annotations
import random
import re
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from core.types import DataSpec, FieldSpec, GeneratedDataset

_faker_cache: dict[str, Faker] = {}


def _get_faker(locale: str) -> Faker:
    if locale not in _faker_cache:
        _faker_cache[locale] = Faker(locale)
    return _faker_cache[locale]


# ── Alan üreticileri ────────────────────────────────────────────────────────

def _generate_field_value(field: FieldSpec, faker: Faker, row_idx: int) -> Any:
    dtype = field.dtype
    name_lower = field.name.lower()

    # Nullable kontrolü
    if field.nullable and random.random() < 0.08:
        return None

    # Semantik isim eşleştirme (önce bak)
    if dtype == "str":
        val = _semantic_str(name_lower, faker)
        if val is not None:
            if field.pattern and not re.match(field.pattern, str(val)):
                pass  # Pattern uymazsa default'a düş
            else:
                return val

    if dtype == "int":
        lo = int(field.min_val) if field.min_val is not None else 0
        hi = int(field.max_val) if field.max_val is not None else 10_000
        return random.randint(lo, hi)

    if dtype == "float":
        lo = float(field.min_val) if field.min_val is not None else 0.0
        hi = float(field.max_val) if field.max_val is not None else 1000.0
        return round(random.uniform(lo, hi), 4)

    if dtype == "bool":
        return random.choice([True, False])

    if dtype == "category":
        if field.categories:
            return random.choice(field.categories)
        return faker.word()

    if dtype == "datetime":
        lo_str = field.min_val or "2020-01-01T00:00:00"
        hi_str = field.max_val or "2025-12-31T23:59:59"
        lo_dt = datetime.fromisoformat(lo_str)
        hi_dt = datetime.fromisoformat(hi_str)
        delta = hi_dt - lo_dt
        rand_sec = random.randint(0, int(delta.total_seconds()))
        return (lo_dt + timedelta(seconds=rand_sec)).isoformat()

    if dtype == "str":
        if field.pattern:
            # Basit pattern'lar için Faker'ın bothify/numerify kullan
            return faker.bothify(text=field.pattern[:20])
        return faker.sentence(nb_words=4)

    return None


def _semantic_str(name: str, faker: Faker) -> str | None:
    """Alan ismine göre anlamlı faker değeri seç."""
    mapping = {
        # Kişisel
        "name": faker.name,
        "first_name": faker.first_name,
        "last_name": faker.last_name,
        "email": faker.email,
        "phone": faker.phone_number,
        "username": faker.user_name,
        "password": lambda: faker.password(length=12),
        "bio": faker.text,
        # Adres
        "address": faker.address,
        "city": faker.city,
        "country": faker.country,
        "zip": faker.postcode,
        "state": faker.state if hasattr(faker, "state") else faker.city,
        # İş
        "company": faker.company,
        "job": faker.job,
        "department": faker.job,
        # Ürün / e-ticaret
        "product": faker.catch_phrase,
        "description": faker.paragraph,
        "sku": lambda: faker.bothify("SKU-????-####"),
        "category": faker.word,
        # Web
        "url": faker.url,
        "ip": faker.ipv4,
        "user_agent": faker.user_agent,
        # Para
        "currency": lambda: random.choice(["USD", "EUR", "TRY", "GBP"]),
        # Genel
        "title": faker.sentence,
        "comment": faker.paragraph,
        "content": faker.text,
        "status": lambda: random.choice(["active", "inactive", "pending"]),
        "uuid": faker.uuid4,
        "id": faker.uuid4,
    }
    for key, fn in mapping.items():
        if key in name:
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

    # Cross-field constraint uygulaması (basit: end > start gibi)
    records = _apply_constraints(records, spec.constraints)

    return GeneratedDataset(
        spec=spec,
        records=records,
        metadata={"generator": "tabular", "locale": spec.locale},
    )


def _apply_constraints(
    records: list[dict], constraints: list[str]
) -> list[dict]:
    """
    Basit constraint enforcement.
    Şu an sadece "field_a > field_b" tipini destekler.
    Daha karmaşık constraint'ler için validator+refiner döngüsüne bırakılır.
    """
    for constraint in constraints:
        # end_time > start_time gibi datetime sıralama kısıtları
        match = re.match(r"(\w+)\s*>\s*(\w+)", constraint)
        if match:
            bigger, smaller = match.group(1), match.group(2)
            for row in records:
                if bigger in row and smaller in row:
                    try:
                        b = datetime.fromisoformat(str(row[bigger]))
                        s = datetime.fromisoformat(str(row[smaller]))
                        if b <= s:
                            row[bigger] = (s + timedelta(hours=random.randint(1, 72))).isoformat()
                    except (ValueError, TypeError):
                        pass
    return records
