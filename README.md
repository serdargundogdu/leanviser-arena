# LeanViser ARENA

Oyunlaştırılmış **yalın üretim simülasyon** platformu. Katılımcı, bir üretim
hattını yönetir; sistem **temin süresi (lead time)**, **akış verimliliği (flow
efficiency)** ve **teslim güvenilirliği (delivery reliability)** üzerinden geri
bildirim verir — **çok üretmek (throughput) ödüllendirilmez**.

> **Sürüm 0.9 — izole keşif.** Yalnızca lokal geliştirme + test. Public yayın,
> gerçek lead / kişisel veri toplama YOK. Tüm veri **sentetik ve tohumludur**;
> bu bir ERP/MES değildir. Ayrıntılı proje sınırları için `CLAUDE.md`.
>
> **v0.3:** takt tabanlı talep programı + teslim-kapılı skor
> (`skor = akış kalitesi × teslim güvenilirliği`) — ne aşırı üretim ne de
> hattı starve etmek kazandırır; yalnız takt'a dengeli akış kazanır.
> **v0.4:** kural-tabanlı koçluk ("FATİH USTA diyor ki") — skoru açıklayan ipuçları.
> **v0.5:** Kümülatif Akış Diyagramı (CFD) — WIP ve temin süresini zaman
> içinde görselleştirir.
> **v0.6:** kaizen kredi bütçesi — kaldıraç hamleleri kredi harcar; iyileştirme
> bedava değildir, doğru tahsis kazandırır (sunucu bütçeyi uygular, aşım 422).
> **v0.7:** 3. kaldıraç **Standart İş** (değişkenlik azaltma) — bütçe 22;
> değişkenlik = kuyruğun kaynağı dersi (74 → 89), ama standart iş büyük
> partiyi kurtaramaz.
> **v0.8:** çoklu senaryo — **Kararsız Hat**: yapı yalın ama CV≈1; tek ödeyen
> düzeltme standart iş (45 → 81), yanlış tahsis hamlesizlikten beter. Teşhis
> reçeteden önce gelir.
> **v0.9:** **Çekme Hattı** (pull/CONWIP) — motor artık salım temposunu WIP
> tavanıyla BİRLEŞTİRİR; kaotik hatta dikkatli çizelge 27'de kalırken girişte
> backlog + içeride tavan 4.5 krediye 74 yapar. Çizelge değişikliği bedavadır;
> yapı yatırımı değildir.

## Mimari

Hexagonal (ports & adapters) modüler monolit. Bağımlılık daima içe akar:

```
adapters/  →  application/  →  domain/
```

- `backend/app/domain/simulation/` — **saf, framework-süz** ayrık-olay
  simülasyonu (DES). Tohumlu ve deterministik: aynı `seed` + config → bit-aynı
  sonuç.
- `backend/app/domain/scoring/` — composite skor (saf): akış kalitesi ×
  teslim güvenilirliği (kapı); throughput terim değil.
- `backend/app/domain/scenario/` — senaryo registry'si (`baseline`,
  `unstable_line`, `pull_line`); kaldıraçlar senaryoya göre (parti, salım,
  standart iş, WIP tavanı) + kaizen kredi bütçesi (hamle = kredi; sunucu
  doğrular; kaldıraç değerleri `levers` sözlüğüyle gönderilir).
- `backend/app/domain/coaching/` — kural-tabanlı koçluk (saf; dil-nötr `Insight`).
- `backend/app/application/` — `RunSimulation` ve `RunScenario` use-case'leri
  (engine + metrics + score'u birleştiren ince orkestrasyon).
- `backend/app/adapters/http/` — FastAPI: `GET /health`, `GET /api/scenarios`,
  `POST /api/simulate` (`scenario_id` ile). Kalıcılık/auth YOK (ertelendi).
- `frontend/` — Vite + React + TS, 2D debrief UI (kaldıraçlar + skor kartı +
  koçluk paneli + flow-time röntgeni + kümülatif akış diyagramı). 3D yok.

## Gereksinimler

- Python **3.12** (backend `.python-version` ile sabit; `uv` indirir).
- [uv](https://docs.astral.sh/uv/) (Python paket/ortam yöneticisi).
- Node.js 20+ ve npm (frontend).

## Backend — kurulum, çalıştırma, test

```bash
cd backend

# Ortamı ve bağımlılıkları kur (uv 3.12'yi otomatik getirir)
uv sync --group dev

# Geliştirme sunucusu (http://127.0.0.1:8000)
uv run uvicorn app.main:app --reload
# Sağlık kontrolü:  curl http://127.0.0.1:8000/health  →  {"status":"ok"}

# Lint + format
uv run ruff check .
uv run ruff format .

# Testler (health + determinizm + değişmezler + skor + senaryo + API)
uv run pytest
```

### Skor motoru (hızlı deneme)

```python
from app.application.run_scenario import RunScenarioCommand, run_scenario
from app.domain.scenario.scenario import baseline_scenario

# Kaldıraç değerleri sözlükle verilir; eksik anahtar = kaldıraç varsayılanı.
# İki-kaldıraç düzeltmesi: parti=1 (tek-parça), salım=6 (~takt) → 16 kredi
lean = run_scenario(
    RunScenarioCommand(
        scenario=baseline_scenario(),
        lever_values={"batch_size": 1, "release_interval": 6.0},
    )
)
print(round(lean.score.composite, 1))    # ~74 / 100

# Tam düzeltme: + standart iş (değişkenlik 0.25) → 22 kredi = tüm bütçe
full = run_scenario(
    RunScenarioCommand(
        scenario=baseline_scenario(),
        lever_values={"batch_size": 1, "release_interval": 6.0, "variance_factor": 0.25},
    )
)
print(round(full.score.composite, 1))    # ~89 / 100

# Varsayılanlar (boş sözlük) = parti 5 + flood: akış çöker — çıktı ödüllenmez
push = run_scenario(RunScenarioCommand(scenario=baseline_scenario()))
print(round(push.score.composite, 1))    # ~0 / 100
```

Hattı starve etmek (salım=12) hem skoru çökertir (teslim kapısı) hem de 28
krediyle **bütçe dışıdır** — `run_scenario` `KaizenBudgetExceededError`
fırlatır. Ham DES motoruna `LineConfig` + `run_simulation` ile de erişilebilir
(`delivery_window` = hedef temin süresi, mutlak tarih değil).

## Frontend — kurulum, çalıştırma, build

```bash
cd frontend
npm install
npm run dev      # geliştirme sunucusu (http://localhost:5173)
npm run build    # üretim derlemesi (tsc --noEmit && vite build)
```

> Debrief UI, `/api`'yi Vite proxy ile `http://localhost:8000`'e yönlendirir;
> bu yüzden **backend'in :8000'de çalışıyor olması gerekir**
> (`uv run uvicorn app.main:app --port 8000`).

## Tam yığın (backend + frontend)

İki terminal: backend'i `:8000`, frontend'i `:5173` çalıştır, tarayıcıda
`http://localhost:5173` aç. API'yi doğrudan da deneyebilirsin:

```bash
# Senaryo listesi
curl http://localhost:8000/api/scenarios

# Çekme Hattı'nda pull oyna: girişte backlog (salım 0, bedava) + tavan 3
curl -X POST http://localhost:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"pull_line","levers":{"release_interval":0,"wip_cap":3}}'
```

## Docker (backend)

```bash
cd backend
docker build -t leanviser-arena-backend .
docker run -p 8080:8080 leanviser-arena-backend
# → http://localhost:8080/health
```

## CI/CD

- **`.github/workflows/ci.yml`** — her push/PR'de: ruff (lint + format),
  pytest ve frontend build. `main`'i yeşil tutar.
- **`.github/workflows/deploy.yml`** — Cloud Run deploy **iskeleti**. Etkin
  değildir; açmak için:
  1. Repo **secret**'ları: `GCP_PROJECT`, `GCP_SA_KEY`, `GCP_REGION`.
  2. Repo **variable**'ı: `ENABLE_DEPLOY = "true"`.

  Bunlar ayarlanana dek deploy adımı atlanır (push'lar yeşil kalır).

## Sıradaki dilim (v1.0 adayları)

Skor tablosu / koşu geçmişi — **kalıcılık (DB) kararı gerektirir**; public
yayın da ayrı insan kararı (izole keşif bayrağı). Kapsam bayrakları için
`CLAUDE.md`.
