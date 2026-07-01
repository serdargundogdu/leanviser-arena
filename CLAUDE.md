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
- v0.2'de **composite skor** eklendi: 3 pilar (lead-time · flow efficiency ·
  delivery) ağırlıklı ortalama × 100; **throughput terim DEĞİL**. "Throughput
  ödüllenmez / aşırı üretim WIP'i şişirir" gerçeği hem motor değişmezlerinde
  (`tests/test_simulation_invariants.py`) hem skorda
  (`tests/test_scoring.py`) **testlerle korunur**.

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
backend/    FastAPI + saf DES/scoring domain (domain/application/adapters/shared)
frontend/   Vite + React + TS (2D debrief UI: kaldıraçlar + skor + flow-time)
.github/    CI (ruff+pytest+build) · deploy (Cloud Run iskeleti)
```

Kurulum / çalıştırma / test / deploy → `README.md`.

## Durum ve kapsam bayrakları

**v0.2'de yapıldı:** composite skor (throughput hariç) · tek `baseline` senaryo +
2 akış kaldıracı (`batch_size`, `release_interval`) · durumsuz HTTP API
(`GET /api/scenario`, `POST /api/simulate`) · hero flow-time debrief UI.

**Hâlâ YOK — sonraki dilimler:**
- Talep/takt kısıtı (aşırı-yavaş salımın dejenere "hattı aç bırak" kazancını
  kapatmak) + kredi sistemi + çoklu senaryo/zorluk → v0.3+.
- Zengin debrief (CFD/kümülatif akış), koçluk (FATİH USTA), skor tablosu → v0.3+.
- Benchmark / leaderboard agregasyonu + k-anon → v1.1.
- Kalıcılık / DB şeması, auth, multi-tenant → sonraki dilim.
- Three.js / 3D fabrika → v2.x.
- LeanViser Core entegrasyonu → port bırak, adapter YOK.
- Yamazumi / çekme challenge'ları → v2.0 (motor jenerik olduğu için genişler).
