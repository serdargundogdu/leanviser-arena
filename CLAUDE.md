# CLAUDE.md — leanviser-arena

Bu dosya, sonraki oturumların **ilk okuyacağı** kılavuzdur. Proje kimliğini,
kilitli mimariyi, dil kuralını ve sınır bayraklarını burada tutuyoruz. Kod ve
kararlar bu çerçevenin dışına **insan onayı olmadan** çıkmaz.

## Proje kimliği (değişmez)

- **leanviser-arena** = oyunlaştırılmış yalın üretim **SİMÜLASYON** platformu.
  İş amacı: görünürlük + kurumsal lead (talep-üretim). Kök adres (ileride):
  `arena.leanviser.app`.
- Bu bir **ERP/MES DEĞİL** — gerçek telemetri / makine / stok verisi YOK; tüm
  veri **sentetik / tohumlu**.
- Bu, LeanViser iç uygulaması **CONSOLE DEĞİL**, çok-kiracılı **Partner
  Platformu DEĞİL**, "Yalın İkiz" (**DTA**) **DEĞİL** — adı/kavramı karıştırma.
- **İZOLE KEŞİF (spike):** v0.1 lokal geliştirme + test. **PUBLIC YAYIN YOK**,
  gerçek lead / kişisel veri toplama YOK. (Yayın + track kalıcılaştırma = ayrı
  insan kararı.)
- **KVKK:** kişi değil **ROL**; v0.1'de kişisel/şirket verisi YOK. Benchmark
  ileride **k-anonim** (şirket kimliği ifşa edilmez).

## Tez (ürünün kalbi — koda gömülü)

- **SKORLAMA TEZİ:** ödül **lead-time** (temin süresi), **flow efficiency**
  (akış verimliliği) ve **delivery reliability** (teslim güvenilirliği) üzerinden
  gelir — **throughput (çıktı) DEĞİL**. Çok üretmek kazandırmaz; hızlı-dengeli
  akış kazanır.
- **Skor (v0.2→v0.3):** akış kalitesi (lead-time + flow efficiency, ağırlıklı)
  **× teslim güvenilirliği** (kapı/gate): `composite = 100 · flow_quality ·
  deliveryReliability`. Talep **takt** temposunda gelir; sipariş k'nın vadesi
  `k·takt + delivery_window`. **Throughput terim DEĞİL.** Aşırı üretim akış
  kalitesini düşürür; aşırı-yavaş salım (starving) teslim kapısını düşürür —
  ikisi de ödül değil, yalnız takt'a-akış kazanır. Korumalar:
  `tests/test_scoring.py`, `tests/test_demand_takt.py`,
  `tests/test_simulation_invariants.py`.

## Mimari (kilitli — Arena-Plan Faz 3)

- Tek **modüler monolit**; **hexagonal** (ports & adapters):
  `domain/` (saf, framework-süz) → `application/` (use case) →
  `adapters/` (FastAPI, DB, dış). Bağımlılık **daima içe** akar; domain HTTP/DB
  bilmez.
- Simülasyon + skorlama **SUNUCU-TARAFLI ve DETERMİNİSTİK** domain servisidir
  (istemci hesaplamaz — otorite + kopya-koruma).
- DES motoru **İSTASYON-JENERİK** kurulur (N istasyon, per-istasyon iş içeriği)
  → ileride Yamazumi / çekme aynı motoru genişletir. Tek-hat = özel hâl.
- Domain framework-süz birim test edilir; iş kuralı / değişmezler domain'de
  (anemik model yok).
- **Forward-compat:** `RunSimulation` komutu actor/company kimliğini taşır
  (v0.1'de kullanılmıyor); auth / multi-tenant / DB bu turda YOK.

## Stack

- **Backend:** Python 3.12 + FastAPI. Test: pytest. Lint/format: ruff.
  Bağımlılık: **uv**. Domain katmanı **yalnız stdlib** kullanır (numpy yok) →
  tohumlu `random.Random(seed)` ile bit-aynı tekrar.
- **Frontend:** React + Vite + TypeScript — v0.2'de 2D debrief UI (2 kaldıraç
  + skor kartı + hero flow-time röntgeni). Dev'de `/api` Vite proxy ile
  backend'e gider. **Three.js EKLENMEZ** (3D ertelendi).
- **Dağıtım:** GCP Cloud Run + GitHub Actions CI/CD; backend `Dockerfile`.

## Dil kuralı

- Konuşma / yorum / doküman: **Türkçe**.
- Kod, tanımlayıcı, dosya adı, commit mesajı, DB: **İngilizce**.
- Son-kullanıcı UI metni: **Türkçe**.

## Çalışma yöntemi (PDCA / Kaizen)

1. Önce kısa plan + dosya ağacı sun, **ONAY BEKLE**.
2. Onay sonrası uygula; **küçük İngilizce commit'ler**.
3. Bitince özet: ne değişti + nasıl çalışır + sıradaki aday.

**AI önerir, insan onaylar:** kilitli kararı veya yeni kapsamı tek başına açma;
belirsizlikte varsayımını yaz ve sor. Simülasyon sentetik veridir; "gerçek
ölçüm" gibi sunma.

## Ubiquitous Language (kod/DB İngilizce · UI Türkçe)

| Türkçe | Kod/DB |
|---|---|
| Sipariş | `Order` |
| İstasyon | `Station` |
| Hat | `ProductionLine` |
| Tur | `Round` |
| Senaryo | `Scenario` |
| Koşu | `Run` |
| Temin süresi | `leadTime` |
| Katma-değerli süre | `valueAddedTime` |
| Akış verimliliği | `flowEfficiency` |
| Süreçteki iş | `WIP` (`workInProcess`) |
| Çıktı hızı | `throughput` |
| Teslim güvenilirliği | `deliveryReliability` |
| Teslim penceresi | `deliveryWindow` |
| Çevrim süresi | `cycleTime` |
| Takt süresi | `taktTime` |
| Parti | `batchSize` |
| Darboğaz | `bottleneck` |
| Kaldıraç | `Lever` |
| Kredi | `credit` |
| Tohum | `seed` |
| Ayrık-olay simülasyonu | `DES` |
| Skor | `score` |
| Anonim benchmark | `anonymizedBenchmark` |
| Yüzdelik | `percentile` |

## Depo yapısı

```
backend/    FastAPI + saf domain (simulation/scoring/scenario/coaching) + application/adapters
frontend/   Vite + React + TS (2D debrief: kaldıraçlar + skor + koçluk + flow-time + CFD)
.github/    CI (ruff+pytest+build) · deploy (Cloud Run iskeleti)
```

Kurulum / çalıştırma / test / deploy → `README.md`.

## Durum ve kapsam bayrakları

**v0.2'de yapıldı:** composite skor · tek `baseline` senaryo + 2 akış kaldıracı
(`batch_size`, `release_interval`) · durumsuz HTTP API · hero flow-time debrief UI.

**v0.3'te yapıldı:** takt tabanlı talep programı (`due_k = k·takt + window`) +
teslim-kapılı skor (gate) → aşırı-yavaş salımın dejenere "hattı aç bırak"
kazancı **kapandı**; debrief şeridi talebe-yetişme durumuna göre renklenir.

**v0.4'te yapıldı:** kural-tabanlı koçluk (`domain/coaching`) — skoru açıklayan,
kaldıraca-bağlı dil-nötr `Insight` kodları (UI Türkçe'ye çevirir); debrief'te
"FATİH USTA diyor ki" paneli. Koçluk yalnız yorumlar, skoru değiştirmez.

**v0.5'te yapıldı:** Kümülatif Akış Diyagramı (CFD) — API sipariş-bazında
salım/tamamlanma zamanlarını açar; debrief'te salınan vs tamamlanan eğrileri +
WIP bandı (bağımlılıksız SVG). Additive; motor/skor dokunulmadı.

**v0.6'da yapıldı:** kaizen kredi bütçesi — kaldıraç hamleleri kredi harcar
(varsayılan bedava; maliyet UYGULANAN değer üstünden), `baseline` bütçesi 16 =
tam düzeltmenin maliyeti (ölçüldü: 15 kredi kötü tahsis ≈ 35 puan, 16 doğru
tahsis ≈ 74). Sunucu-otoriter: `run_scenario` bütçeyi uygular, API aşımı 422
döner; UI canlı maliyet + bar gösterir. NOT: `build_config` bütçe UYGULAMAZ
(bilinçli) — tez/fizik testleri bütçe-dışı konfigleri domain seviyesinde
problamaya devam eder (`test_demand_takt.py`, `test_coaching.py`).

**Hâlâ YOK — sonraki dilimler:**
- 3. kaldıraç (`wip_cap` — motorda hazır): bütçe 16'yı gerçek kıtlığa çevirir
  (üç kaldıracın tamamına yetmez) → v0.7 adayı.
- Çoklu senaryo/zorluk, skor tablosu → v0.7+.
- Benchmark / leaderboard agregasyonu + k-anon → v1.1.
- Kalıcılık / DB şeması, auth, multi-tenant → sonraki dilim.
- Three.js / 3D fabrika → v2.x.
- LeanViser Core entegrasyonu → port bırak, adapter YOK.
- Yamazumi / çekme challenge'ları → v2.0 (motor jenerik olduğu için genişler).
