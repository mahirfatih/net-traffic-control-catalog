# Net Traffic Control Catalog — Proje Denetim ve Geliştirme Raporu (Audit)

**Tarih:** 20 Ekim 2026  
**Kapsam:** Veri tutarlılığı, pipeline güvenilirliği, test kapsama alanı, otomasyon, dökümantasyon ve mimari analiz.

---

## 1. Yönetici Özeti (Executive Summary)

`net-traffic-control-catalog`, iOS Net Traffic Control uygulaması için ana domain-kategori ve servis haritalamasını sağlayan son derece titiz tasarlanmış, savunmacı (defensive) mimariye sahip bir veri deposudur.

Mevcut durumda:
- **6.731 host**, **27 kategori** ve **22 servis** tanımlıdır.
- DNS kontrolü (dead-domain sweep), RDAP/WHOIS kontrolü (registration verify) ve HTTP/Headless tarama (live sweep) olmak üzere **3 bağımsız kapı** ile çalışmaktadır.
- `test/test.sh` paketi şemadan kural çakışmalarına, lisanstan doküman tazeliğine kadar kapsamlı doğrulamalar yapmaktadır.

Bununla birlikte, repo derinlemesine incelendiğinde veri dengesizliği, pipeline tazeleme otomasyonu, etiket doğrulukları ve test süreçlerinde geliştirilmeye açık önemli noktalar tespit edilmiştir.

---

## 2. Tespit Edilen Eksiklikler ve Bulgular (Findings)

### 2.1. Kritik Veri Dağılımı Dengesizliği (Category Imbalance & Source Concentration)
- **Finans Dominansı (%53):** Katalogdaki 6.731 hostun 3.571'i (%53) `finance` kategorisindedir.
- **Tek Kaynak Bağımlılığı:** Finans kategorisindeki hostların 3.491'i (%98) tek bir kaynaktan (`adguard-https-exclusions-banks`) gelmektedir.
- **Zayıf Sinyalli Domainler:** `test/test.sh` çalıştığında uyarı verdiği üzere, AdGuard banka listesinden içeri aktarılan **1.477 finans hostu leksikal/semantik olarak zayıf finans sinyaline** sahiptir (`1.elecsnet.ru`, `1822direkt.de` vb.).
- **Güdük (Thin) Kategoriler:** `maps` (3), `sports` (7), `crypto` (10), `music` (10), `crash` (13), `telecom` (16), `other` (14) kategorilerinde çok az örnek bulunmaktadır. Bu durum ML modellerinde dengeli doğruluğu (balanced accuracy) %61 seviyesine düşürmektedir.

### 2.2. Somut Yanlış Etiketleme (Concrete Mislabeling) Tespiti
- **`guven.com.tr` Hatası:**
  - `seeds/categories.json` içerisinde `finance` olarak etiketlenmiştir.
  - `docs/analysis/finance-triage.md` ve `docs/analysis/README.md` dosyalarında *"güven = trust kelimesinden ötürü sigortacı olabilir"* şeklinde not düşülmüştür.
  - Ancak `evidence/live-sweep.json` kanıtında açıkça görüldüğü üzere final başlığı: **`"Ana Sayfa | Güven Hastanesi"`** şeklindedir.
  - Bu alan adı Türkiye'nin köklü özel sağlık kuruluşlarından **Güven Sağlık Grubu / Güven Hastanesi**'ne aittir ve kategorisi kesinlikle **`health`** olmalıdır.

### 2.3. İncelenmemiş Devasa Kaynak Havuzu (Unmatched Backlog: 3.611 Host)
- `docs/NEEDS-REVIEW.md` dosyasında belgelendiği üzere, upstream kaynaklardan gelen fakat hiçbir kural ile eşleşmeyen **3.611 benzersiz host (3.618 kaynak referansı)** `evidence/pending-source-hosts.json` içinde beklemektedir.
- Elle incelenmiş host sayısı ise yalnızca 1'dir (`api.rlje.net`). Bu büyük potansiyel veri havuzunu kurallara bağlayacak yarı-otonom triage / öneri mekanizması eksiktir.

### 2.4. Geriye Dönük Menşe Boşluğu (Seeds Provenance Gap)
- Katalogdaki 6.731 hostun **2.154 adedi** kuruluş döneminden kaldığı için menşesizdir (`evidence/seeds-only.json`).
- `seeds/hand-added.json` (Door 3) mekanizması kurulmuş fakat henüz içi boştur (`"added": {}`). Elle eklenen hostların kim tarafından, ne zaman ve hangi gerekçeyle eklendiğini kayıt altına alan bu sistem aktif olarak kullanılmamaktadır.

### 2.5. HTML Text Çıkarımı ve JS Tabanlı Sitelerdeki Kapsama Eksikliği
- Katalogdaki 6.731 hostun sadece 4.563'ü (%68) metin analizi için okunabilmektedir. 2.168 host metin üretememektedir.
- Özellikle `gaming` kategorisindeki hostların yalnızca %19'u, `cdn` kategorisinin %31'i, `software` kategorisinin %35'i taranabilmektedir. Bu durum Single Page Application (SPA / React / Canvas) yapısındaki sitelerin düz HTTP `fetch` ile boş dönmesinden kaynaklanmaktadır. `agent-browser` + Lightpanda fallback'i mevcuttur ancak tarama sürecinin ana hattına tam entegre edilmesi gerekmektedir.

### 2.6. `catalog.json` Üretim Determinizmi ve `test.sh` Yan Etkisi
- `test/test.sh` çalıştırıldığında `scripts/catalog/generate.py` tetiklenmekte ve `catalog.json` dosyasındaki `"generated": "YYYY-MM-DD"` alanını günün tarihine güncellemektedir.
- Bu durum depoda istem dışı bir `git diff` (dirty working tree) oluşmasına yol açmaktadır. Test çalıştırıldığında dosya içeriği doğrulanmalı ancak salt test modunda diskteki dosyayı kirletmemeli veya geçici bir çıktı ile karşılaştırma yapmalıdır.

---

## 3. "Şunu da Yap" Öneri Listesi (Actionable Recommendations)

Aşağıdaki maddeler öncelik sırasına göre gruplandırılmıştır:

### 🚨 Yüksek Öncelik (Quick Wins & Bug Fixes)

1. **`guven.com.tr` Alan Adını Düzelt:**
   - `seeds/categories.json` dosyasında `"guven.com.tr": "finance"` yerine `"health"` olarak güncellenmelidir.
   - İlgili analiz dokümanları (`docs/analysis/finance-triage.md`, `README.md`) bu doğrultuda güncellenmelidir.
2. **`test.sh` İçin `--check` veya Kuru Çalıştırma (Dry-Run) Modu:**
   - `generate.py` scriptine `--check` parametresi eklenmeli; `catalog.json` dosyasını sadece disktekiyle farkı var mı diye bellek üzerinde doğrulamalı, dosyaya yazarak git çalışma ağacını kirletmemelidir.
3. **`hand-added.json` Kullanımını Başlat:**
   - Yeni elle eklenen hostların doğrudan `seeds/categories.json` yerine `seeds/hand-added.json` üzerinden geçmesi zorunlu kılınmalıdır.

---

### ⚙️ Orta Öncelik (Pipeline ve Süreç İyileştirmeleri)

4. **Pending Hostlar İçin Yarı-Otomatik Triage CLI Aracı:**
   - 3.611 bekleyen host için `scripts/sources/` altına bir triage CLI aracı eklenmelidir.
   - Araç; hostun DNS kaydına bakmalı, ana sayfa `<title>` bilgisini çekmeli ve `rules.json` için olası regex/suffix kurallarını operatöre önermelidir.
5. **Düşük Temsilli Kategorilerin Güçlendirilmesi (Thin Classes Expansion):**
   - `maps` (3), `sports` (7), `crypto` (10), `music` (10), `telecom` (16) kategorileri için güvenilir açık kaynaklı seed listeleri bulunmalı ve `sources.json`'a eklenmelidir.
   - Bu sayede ML modelinin Macro F1 skoru ve kategori dengesi belirgin şekilde yükselecektir.
6. **Banka / Finans Listesi Temizliği:**
   - `adguard-https-exclusions-banks` içerisindeki zayıf sinyalli 1.477 host taranarak finans dışı altyapı/reklam/ödeme harici domainler elenmelidir.

---

### 🛡️ İleri Seviye (Altyapı, Otomasyon & Güvenlik)

7. **Otomatik Sweep Zamanlaması (Cron Workflow):**
   - `.github/workflows/sweep.yml` periyodik olarak (örneğin ayda bir) çalışacak şekilde `schedule` cron tetikleyicisine bağlanmalı ve sonuçları otomatik bir PR (Pull Request) olarak açmalıdır.
8. **Subdomain Çözümleme Derinliği:**
   - Mobil uygulamalarda sıkça karşılaşılan `api.*`, `auth.*`, `login.*` gibi mikro servis domainlerinin katalogda ana domain ile çelişip çelişmediğini denetleyen kurallar zenginleştirilmelidir.
9. **Katalog Sürümleme ve Dağıtım:**
   - Shipped `catalog.json` dosyasının istemciler tarafından tüketimi için bir SHA256 checksum dosyası (`catalog.json.sha256`) ve sıkıştırılmış sürümü (`catalog.json.gz` veya `br`) derleme sürecine dahil edilmelidir.

---

## 4. Sonuç

Proje, mimari prensipler, veri hijyeni ve dokümantasyon disiplini açısından çok üst düzey bir standarttadır. Yukarıdaki maddelerin hayata geçirilmesi, özellikle veri kalitesini ve otomasyon güvenliğini bir üst seviyeye taşıyacaktır.
