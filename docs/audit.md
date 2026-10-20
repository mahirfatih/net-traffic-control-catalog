# Net Traffic Control Catalog — Güncel Proje Audit’i

**Tarih:** 20 Ekim 2026  
**Kapsam:** veri kalitesi, pipeline, testler, CI/CD, release, reproducibility ve dokümantasyon.

## Yönetici özeti

Repo şu anda temiz, lineer ve çalışır durumda. `./test/test.sh --fast` tüm
kontrolleri geçti. Catalog üretimi deterministik, lisans kapıları mevcut,
CI push ve pull request’lerde çalışıyor; sweep’ler ise veri değiştirmeden
öneri üretiyor.

Mevcut ana riskler veri kapsamı ve release sözleşmesindedir:

- `seeds/categories.json`: 6.731 host ve 27 kullanılan kategori.
- `seeds/services.json`: 22 servis.
- `evidence/pending-source-hosts.json`: 3.611 benzersiz incelenmemiş host.
- `evidence/seeds-only.json`: tarihsel provenance’ı olmayan 2.154 host.
- Analiz snapshot’larında HTML metni üretilemeyen hostlar bulunuyor; SPA ve
  anti-bot siteleri klasik HTTP fetch ile ölçülemiyor.

## Bulgular

### Açık bulgular

| # | Öncelik | Alan | Bulgu | Önerilen çözüm |
|---|---|---|---|---|
| 1 | HIGH | Veri kalitesi | `finance` kategorisi katalogda baskın; tek kaynak yoğunluğu model ölçümlerini etkiliyor. | Zayıf sinyalli finans hostlarını örneklem bazlı tekrar incele; kaynak katkısını bağımsız kanıtla destekle. |
| 2 | HIGH | Provenance | 2.154 tarihsel hostun menşei dosya düzeyinde açıklanamıyor. | Yeni eklemelerde provenance’ı zorunlu tut; eski hostları batch’ler halinde kaynak veya karar kaydıyla kapat. |
| 3 | MEDIUM | Backlog | 3.611 pending host için operatör destekli triage akışı yeni eklendi; karar hâlâ manuel. | `scripts/sources/triage-pending.py` ile batch worksheet üret; yalnızca insan onayından sonra seed/rule değiştir. |
| 4 | MEDIUM | Analiz | JS/SPA sitelerinde HTTP metin kapsamı sınırlı. | Browser fallback sonuçlarını ana analiz formatına dahil et; fetch/browser ayrımını metriklerde görünür tut. |
| 5 | MEDIUM | Reproducibility | Analiz bağımlılıkları artık tam snapshot ile tutuluyor ancak hash doğrulaması yok. | Lockfile’ı hash’li üretimle ve model checksum’ıyla güçlendir. |
| 6 | LOW | Repository boyutu | Büyük sweep JSON snapshot’ları clone ve review maliyetini artırıyor. | Uzun dönemli ham çıktıları artifact/object storage’a taşı; repo’da özet ve checksum bırak. |

### Kapatılan bulgular

| Konu | Durum |
|---|---|
| `guven.com.tr` yanlış kategorisi | Kapatıldı: `health` olarak düzeltildi ve ilgili dokümanlar yenilendi. |
| `generate.py --check` eksikliği | Kapatıldı: `--check` mevcut ve testte çalıştırılıyor. |
| Test sırasında istemsiz catalog değişimi | Kapatıldı: doğrulama yolu yazmadan karşılaştırma yapıyor; test paketi yeşil. |
| Audit dokümanının indexlenmemesi | Kapatıldı: bu dosya `docs/README.md` içinde listeleniyor. |

## Release ve CI kontrolleri

- Format sürümü artık generator, validator, schema ve test sözleşmesiyle
  birlikte güncelleniyor.
- `bump-version.sh` sıfır ve geriye dönük sürüm artışlarını reddediyor.
- GitHub Actions bağımlılıkları commit SHA’lerine pinlendi.
- CI ve scheduled sweep için timeout sınırları var.
- DNS sweep haftalık scheduled proposal üretir; hiçbir catalog dosyasını
  otomatik değiştirmez.

## Öncelikli sonraki işler

1. Pending host triage CLI ve operatör worksheet’i.
2. Provenance backlog’unun batch’ler halinde kapatılması.
3. Finance kaynak yoğunluğu için precision örneklemi.
4. Hash’li analiz dependency lockfile ve model metadata’sı.
5. Büyük evidence snapshot’ları için artifact politikası.

## Son doğrulama

```text
./test/test.sh --fast  -> all checks passed
working tree           -> clean
```
