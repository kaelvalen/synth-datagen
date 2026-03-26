# SynthForge 🔧

Doğal dil promptlarından kusursuz sentetik veri üreten güçlü bir araç.

## Özellikler

- 🗣️ **Doğal Dil Desteği**: Veri setinizi doğal dil ile tanımlayın
- 📊 **Çoklu Veri Tipleri**: Tabular, NLP, Timeseries, Log
- ✅ **Akıllı Validasyon**: LLM destekli kalite kontrolü
- 🔄 **Otomatik İyileştirme**: Hataları otomatik düzelten refine döngüsü
- 📦 **Çoklu Export Formatı**: CSV, JSONL, Parquet, SQL, Excel, TXT
- 🎯 **Hazır Şablonlar**: E-commerce, User, Metrics, Logs için hazır spec'ler
- 🔁 **Reproducibility**: Seed desteği ile tekrarlanabilir sonuçlar

## Kurulum

```bash
# Clone the repository
git clone https://github.com/yourusername/synthforge.git
cd synthforge

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-api-key"
```

## Hızlı Başlangıç

### CLI Kullanımı

```bash
# Basit kullanım
python cli.py "e-ticaret sipariş verisi üret" --type tabular --rows 500 --format csv

# NLP veri seti
python cli.py "ürün yorumları ve sentiment analizi" --type nlp --rows 100 --format jsonl

# Zaman serisi
python cli.py "sunucu CPU ve bellek metrikleri" --type timeseries --rows 1000 --format parquet

# Log verisi
python cli.py "API erişim logları" --type log --rows 2000 --format sql

# Dry run - sadece spec'i göster
python cli.py "kullanıcı profilleri" --type tabular --dry-run

# Seed ile reproducibility
python cli.py "test verisi" --type tabular --rows 50 --seed 42

# Sıkıştırılmış çıktı
python cli.py "büyük veri seti" --type tabular --rows 10000 --compress
```

### Python API

```python
from pipeline import run
from core.types import DataType, ExportFormat

# Basit kullanım
result = run(
    prompt="E-commerce sipariş verisi: müşteri bilgileri, ürün detayları, fiyatlar",
    data_type=DataType.TABULAR,
    row_count=500,
    export_format=ExportFormat.CSV,
    output_dir="./output",
)

print(f"Üretilen kayıt sayısı: {len(result.dataset.records)}")
print(f"Validation score: {result.validation.score}")
print(f"Dosya: {result.export_path}")
```

### Şablon Kullanımı

```python
from templates.specs import get_template, list_templates
from pipeline import _generate
from exporters.writer import export
from core.types import ExportFormat

# Mevcut şablonları listele
print(list_templates())
# ['ecommerce_orders', 'ecommerce_products', 'user_profiles', ...]

# Şablon al ve kullan
spec = get_template("ecommerce_orders")
spec.row_count = 1000  # İsteğe göre ayarla

dataset = _generate(spec)
export(dataset, ExportFormat.CSV, output_dir="./output")
```

## CLI Seçenekleri

| Seçenek | Kısa | Açıklama |
|---------|------|----------|
| `--type` | `-t` | Veri tipi: `tabular`, `nlp`, `timeseries`, `log` |
| `--rows` | `-r` | Üretilecek kayıt sayısı (varsayılan: 100) |
| `--format` | `-f` | Çıktı formatı: `csv`, `jsonl`, `parquet`, `sql`, `xlsx`, `txt` |
| `--output` | `-o` | Çıktı dizini (varsayılan: `./output`) |
| `--seed` | | Reproducibility için random seed |
| `--no-validate` | | Validation döngüsünü atla (daha hızlı) |
| `--max-refine` | | Maksimum refine iterasyonu (varsayılan: 3) |
| `--dry-run` | | Sadece spec'i göster, veri üretme |
| `--compress` | | Çıktıyı gzip ile sıkıştır |
| `--quiet` | `-q` | Sadece sonuç göster |
| `--verbose` | `-v` | Detaylı çıktı |
| `--config` | | YAML config dosyası |

## Veri Tipleri

### Tabular
Yapılandırılmış tablo verisi. E-commerce, kullanıcı profilleri, finansal veriler için ideal.

```bash
python cli.py "müşteri siparişleri: ad, email, ürün, fiyat, tarih" --type tabular
```

### NLP
Doğal dil metinleri. Yorumlar, destek talepleri, açıklamalar için.

```bash
python cli.py "ürün incelemeleri: başlık, yorum, puan, sentiment" --type nlp
```

### Timeseries
Zaman serisi verisi. Sensör okumaları, sunucu metrikleri, finansal veriler için.

```bash
python cli.py "IoT sıcaklık ve nem sensörleri" --type timeseries
```

### Log
Sistem ve uygulama logları. HTTP logları, uygulama eventleri için.

```bash
python cli.py "microservice application logs" --type log
```

## Export Formatları

| Format | Açıklama | Kullanım Alanı |
|--------|----------|----------------|
| `csv` | Comma-separated values | Excel, pandas, genel amaçlı |
| `jsonl` | JSON Lines | Streaming, ML pipelines |
| `parquet` | Apache Parquet | Big data, Spark, analitik |
| `sql` | SQL INSERT statements | Veritabanı import |
| `xlsx` | Excel workbook | Excel kullanıcıları |
| `txt` | Plain text | NLP veri setleri |

## Hazır Şablonlar

| Şablon | Tip | Alanlar | Açıklama |
|--------|-----|---------|----------|
| `ecommerce_orders` | tabular | 15 | E-commerce sipariş verisi |
| `ecommerce_products` | tabular | 15 | Ürün kataloğu |
| `user_profiles` | tabular | 16 | Kullanıcı profilleri |
| `server_metrics` | timeseries | 12 | Sunucu metrikleri |
| `iot_sensors` | timeseries | 8 | IoT sensör verileri |
| `http_logs` | log | 12 | HTTP erişim logları |
| `app_logs` | log | 9 | Uygulama logları |
| `product_reviews` | nlp | 14 | Ürün yorumları |
| `support_tickets` | nlp | 13 | Destek talepleri |
| `transactions` | tabular | 11 | Finansal işlemler |

## Proje Yapısı

```
synthforge/
├── cli.py              # CLI entry point
├── pipeline.py         # Ana pipeline orchestration
├── core/
│   ├── types.py        # Data models (DataSpec, FieldSpec, etc.)
│   ├── llm.py          # LLM client (Anthropic)
│   └── console.py      # Rich console utilities
├── intent/
│   └── parser.py       # Prompt → DataSpec dönüşümü
├── generators/
│   ├── tabular.py      # Tabular veri üretici
│   ├── nlp.py          # NLP veri üretici
│   ├── timeseries.py   # Zaman serisi üretici
│   └── log.py          # Log veri üretici
├── validators/
│   └── checker.py      # Kural + LLM validasyon
├── refiners/
│   └── refiner.py      # Veri iyileştirme
├── exporters/
│   └── writer.py       # Multi-format export
├── templates/
│   └── specs.py        # Hazır veri şablonları
├── tests/
│   ├── conftest.py     # Test fixtures
│   ├── test_*.py       # Unit & integration tests
└── output/             # Çıktı dizini
```

## Geliştirme

### Testleri Çalıştırma

```bash
# Tüm testler
python -m pytest tests/ -v

# Coverage ile
python -m pytest tests/ --cov=. --cov-report=html

# Belirli bir test dosyası
python -m pytest tests/test_generators.py -v
```

### Yeni Bir Generator Ekleme

1. `generators/` altında yeni dosya oluştur
2. `generate(spec: DataSpec) -> GeneratedDataset` fonksiyonu implement et
3. `pipeline.py`'daki dispatch dict'e ekle
4. Test yaz

## Config Dosyası

`config.yaml` örneği:

```yaml
default_rows: 500
default_format: jsonl
output_dir: ./data
max_refine: 5
locale: tr_TR
```

Kullanım:
```bash
python cli.py "veri seti" --type tabular --config config.yaml
```

## Gereksinimler

- Python 3.10+
- Anthropic API key (Claude erişimi için)

## Lisans

MIT License

## Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın
