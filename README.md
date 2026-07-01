# LeanViser ARENA

Oyunlaştırılmış **yalın üretim simülasyon** platformu. Katılımcı, bir üretim
hattını yönetir; sistem **temin süresi (lead time)**, **akış verimliliği (flow
efficiency)** ve **teslim güvenilirliği (delivery reliability)** üzerinden geri
bildirim verir — **çok üretmek (throughput) ödüllendirilmez**.

> **Sürüm 0.4 — izole keşif.** Yalnızca lokal geliştirme + test. Public yayın,
> gerçek lead / kişisel veri toplama YOK. Tüm veri **sentetik ve tohumludur**;
> bu bir ERP/MES değildir. Ayrıntılı proje sınırları için `CLAUDE.md`.
>
> **v0.3:** takt tabanlı talep programı + teslim-kapılı skor
> (`skor = akış kalitesi × teslim güvenilirliği`) — ne aşırı üretim ne de
> hattı starve etmek kazandırır; yalnız takt'a dengeli akış kazanır.
> **v0.4:** kural-tabanlı koçluk ("FATİH USTA diyor ki") — skoru açıklayan,
> eyleme dönük ipuçları.

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
- `backend/app/domain/scenario/` — tek `baseline` senaryo + 2 kaldıraç.
- `backend/app/domain/coaching/` — kural-tabanlı koçluk (saf; dil-nötr `Insight`).
- `backend/app/application/` — `RunSimulation` ve `RunScenario` use-case'leri
  (engine + metrics + score'u birleştiren ince orkestrasyon).
- `backend/app/adapters/http/` — FastAPI: `GET /health`, `GET /api/scenario`,
  `POST /api/simulate`. Kalıcılık/auth YOK (ertelendi).
- `frontend/` — Vite + React + TS, 2D debrief UI (kaldıraçlar + skor kartı +
  koçluk paneli + flow-time röntgeni). 3D yok.

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

# Kaldıraçlar: parti=1 (tek-parça akış), salım=6 (~takt/dengeli)
lean = run_scenario(
    RunScenarioCommand(scenario=baseline_scenario(), batch_size=1, release_interval=6.0)
)
print(round(lean.score.composite, 1))    # ~74 / 100

# Aşırı üretim (parti=5, flood): akış çöker — çıktı ödüllenmez, WIP şişer
push = run_scenario(
    RunScenarioCommand(scenario=baseline_scenario(), batch_size=5, release_interval=0.0)
)
print(round(push.score.composite, 1))    # ~0 / 100

# Hattı starve etmek (parti=1, salım=12): akış kusursuz ama talebe yetişmez
starve = run_scenario(
    RunScenarioCommand(scenario=baseline_scenario(), batch_size=1, release_interval=12.0)
)
print(round(starve.score.composite, 1))  # ~7 / 100 — teslim kapısı düşürür
```

Ham DES motoruna `LineConfig` + `run_simulation` ile de erişilebilir
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
curl -X POST http://localhost:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"batch_size":1,"release_interval":6.0}'
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

## Sıradaki dilim (v0.5 adayı)

Kredi sistemi (kaldıraç maliyeti/bütçe) + zengin debrief (CFD/kümülatif akış) +
çoklu senaryo. Kapsam bayrakları için `CLAUDE.md`.
