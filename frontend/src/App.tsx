// v0.1 placeholder lobby (2D). UI copy is Turkish; no simulation runs here —
// the engine is server-authoritative. Real lobby / scoreboard arrives in v0.2+.
export function App() {
  return (
    <main className="lobby">
      <div className="lobby__card">
        <p className="lobby__eyebrow">LeanViser</p>
        <h1 className="lobby__title">ARENA</h1>
        <p className="lobby__tagline">
          Yalın üretim simülasyon arenası — sürüm 0.1
        </p>

        <p className="lobby__body">
          Arena lobisi hazırlanıyor. Bu sürüm bir yer tutucudur; simülasyon
          motoru ve skorlama sunucu tarafında, deterministik olarak çalışır.
        </p>

        <ul className="lobby__badges">
          <li>Sunucu-otoriter</li>
          <li>Deterministik (tohumlu)</li>
          <li>Sentetik veri</li>
        </ul>
      </div>

      <footer className="lobby__footer">
        Ödül akışın kendisidir: temin süresi, akış verimliliği ve teslim
        güvenilirliği — çıktı miktarı değil.
      </footer>
    </main>
  );
}
