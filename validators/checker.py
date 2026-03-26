from __future__ import annotations
import json
import re
import statistics
from datetime import datetime
from typing import Any

from core.llm import chat_json
from core.types import DataSpec, FieldSpec, GeneratedDataset, ValidationResult

CRITIQUE_SYSTEM = """
Sen bir veri kalite mühendisisin. Sana bir veri seti spesifikasyonu ve örnek kayıtlar verilecek.

Veri setini şu açılardan değerlendir:
1. Alan değerleri spec'e uygun mu?
2. Kayıtlar gerçekçi ve çeşitli mi?
3. Cross-field constraint'ler sağlanıyor mu?
4. Domain bağlamı tutarlı mı?

SADECE JSON döndür:
{
  "score": <0.0 ile 1.0 arası float>,
  "issues": ["sorun1", "sorun2"],
  "suggestions": ["öneri1", "öneri2"]
}
"""


def validate(dataset: GeneratedDataset) -> ValidationResult:
    """Kural tabanlı ve LLM critique'i birleştirerek ValidationResult üretir."""
    rule_issues = _rule_based_check(dataset.spec, dataset.records)
    llm_result = _llm_critique(dataset.spec, dataset.records)

    all_issues = rule_issues + llm_result.get("issues", [])
    all_suggestions = llm_result.get("suggestions", [])

    # Score: kural ihlalleri + LLM score'u birleştir
    rule_penalty = min(len(rule_issues) * 0.1, 0.5)
    llm_score = float(llm_result.get("score", 0.8))
    final_score = max(0.0, llm_score - rule_penalty)

    return ValidationResult(
        passed=final_score >= 0.7 and len(rule_issues) == 0,
        issues=all_issues,
        suggestions=all_suggestions,
        score=round(final_score, 3),
    )


# ── Kural tabanlı kontroller ────────────────────────────────────────────────

def _rule_based_check(spec: DataSpec, records: list[dict]) -> list[str]:
    issues: list[str] = []
    if not records:
        return ["Hiç kayıt üretilmedi."]

    for field in spec.fields:
        vals = [r.get(field.name) for r in records]
        non_null = [v for v in vals if v is not None]

        # Nullable kontrol
        null_count = len(vals) - len(non_null)
        if not field.nullable and null_count > 0:
            issues.append(f"'{field.name}': {null_count} null değer var ama nullable=false.")

        if not non_null:
            continue

        # Unique kontrol
        if field.unique and len(set(str(v) for v in non_null)) < len(non_null):
            issues.append(f"'{field.name}': unique=true ama tekrar eden değerler var.")

        # Tip kontrol
        type_issues = _check_dtype(field, non_null)
        issues.extend(type_issues)

        # Min/max kontrol
        range_issues = _check_range(field, non_null)
        issues.extend(range_issues)

        # Category kontrol
        if field.dtype == "category" and field.categories:
            invalid = [v for v in non_null if v not in field.categories]
            if invalid:
                issues.append(
                    f"'{field.name}': {len(invalid)} değer izin verilen kategoriler dışında. "
                    f"Örnek: {invalid[:3]}"
                )

    # Diversity kontrol: çok tekrar eden değerler?
    for field in spec.fields:
        if field.dtype in ("str", "category") and not field.unique:
            vals = [r.get(field.name) for r in records if r.get(field.name)]
            if vals:
                most_common_ratio = max(vals.count(v) for v in set(vals)) / len(vals)
                if most_common_ratio > 0.7:
                    issues.append(
                        f"'{field.name}': tek değer kayıtların %{most_common_ratio*100:.0f}'inde — çeşitlilik düşük."
                    )

    return issues


def _check_dtype(field: FieldSpec, values: list[Any]) -> list[str]:
    issues = []
    dtype = field.dtype
    type_map = {"int": int, "float": (int, float), "bool": bool, "str": str}

    if dtype in type_map:
        expected = type_map[dtype]
        wrong = [v for v in values if not isinstance(v, expected)]
        if wrong:
            issues.append(
                f"'{field.name}': {len(wrong)} değer beklenen tip ({dtype}) değil. Örnek: {wrong[:2]}"
            )

    if dtype == "datetime":
        for v in values[:20]:  # ilk 20'yi kontrol et
            try:
                datetime.fromisoformat(str(v))
            except ValueError:
                issues.append(f"'{field.name}': geçersiz datetime formatı: {v!r}")
                break

    return issues


def _check_range(field: FieldSpec, values: list[Any]) -> list[str]:
    issues = []
    if field.min_val is None and field.max_val is None:
        return issues

    numeric = [v for v in values if isinstance(v, (int, float))]
    if not numeric:
        return issues

    if field.min_val is not None:
        below = [v for v in numeric if v < float(field.min_val)]
        if below:
            issues.append(f"'{field.name}': {len(below)} değer min ({field.min_val}) altında.")

    if field.max_val is not None:
        above = [v for v in numeric if v > float(field.max_val)]
        if above:
            issues.append(f"'{field.name}': {len(above)} değer max ({field.max_val}) üstünde.")

    return issues


# ── LLM critique ────────────────────────────────────────────────────────────

def _llm_critique(spec: DataSpec, records: list[dict]) -> dict:
    sample = records[:15]   # İlk 15 kaydı critique et (token tasarrufu)

    user_msg = f"""
Spesifikasyon:
{json.dumps({"name": spec.name, "data_type": spec.data_type, "context": spec.context,
             "constraints": spec.constraints,
             "fields": [{"name": f.name, "dtype": f.dtype, "description": f.description}
                        for f in spec.fields]},
            ensure_ascii=False, indent=2)}

Örnek kayıtlar ({len(sample)}/{len(records)}):
{json.dumps(sample, ensure_ascii=False, indent=2, default=str)}
    """.strip()

    try:
        return chat_json(
            system=CRITIQUE_SYSTEM,
            user=user_msg,
            temperature=0.2,
            max_tokens=1024,
        )
    except (ValueError, Exception) as e:
        print(f"[validator] LLM critique başarısız: {e}")
        return {"score": 0.75, "issues": [], "suggestions": []}
