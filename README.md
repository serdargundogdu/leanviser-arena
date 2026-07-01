# LeanViser ARENA

Oyunlaştırılmış **yalın üretim simülasyon** platformu. Katılımcı, bir üretim
hattını yönetir; sistem **temin süresi (lead time)**, **akış verimliliği (flow
efficiency)** ve **teslim güvenilirliği (delivery reliability)** üzerinden geri
bildirim verir — **çok üretmek (throughput) ödüllendirilmez**.

> **Sürüm 0.1 — izole keşif.** Yalnızca lokal geliştirme + test. Public yayın,
> gerçek lead / kişisel veri toplama YOK. Tüm veri **sentetik ve tohumludur**;
> bu bir ERP/MES değildir. Ayrıntılı proje sınırları için `CLAUDE.md`.

## Mimari

Hexagonal (ports & adapters) modüler monolit. Bağımlılık daima içe akar:

```
adapters/  →  application/  →  domain/
```

- `backend/app/domain/simulation/` — **saf, framework-süz** ayrık-olay
  simülasyonu (DES). Tohumlu ve deterministik: aynı `seed` + config → bit-aynı
  sonuç.
- `backend/app/application/` — `RunSimulation` use-case (engine + metrics'i
  birleştiren ince orkestrasyon).
- `backend/app/adapters/` — FastAPI (v0.1: yalnız `GET /health`), ileride DB.
- `frontend/` — Vite + React + TS, 2D placeholder lobi (3D yok).

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

# Testler (health + determinizm + değişmezler)
uv run pytest
```

### Simülasyon çekirdeği (hızlı deneme)

```python
from app.application.run_simulation import RunSimulationCommand, run_simulation
from app.domain.simulation.line import LineConfig, StationSpec

config = LineConfig(
    stations=(
        StationSpec("cut", cycle_time_mean=4.0, cycle_time_variance=1.0),
        StationSpec("weld", cycle_time_mean=6.0, cycle_time_variance=2.0),
        StationSpec("paint", cycle_time_mean=5.0, cycle_time_variance=1.5),
    ),
    order_count=60,
    due_date=800.0,
    seed=7,
    batch_size=1,          # tek-parça akış; büyütünce temin süresi artar
    release_interval=6.0,  # 0.0 = flood (aşırı üretim → WIP şişer)
)
metrics = run_simulation(RunSimulationCommand(config=config))
print(metrics)  # leadTime medyan/ortalama, WIP, flowEfficiency, throughput, deliveryReliability
```

## Frontend — kurulum, çalıştırma, build

```bash
cd frontend
npm install
npm run dev      # geliştirme sunucusu
npm run build    # üretim derlemesi (tsc --noEmit && vite build)
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

## Sıradaki dilim (v0.2 adayı)

Tek senaryo + push tabanı + 2 kaldıraç + **composite skor** + hero flow-time
debrief grafiği. Kapsam bayrakları için `CLAUDE.md`.
