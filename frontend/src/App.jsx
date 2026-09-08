import { useState } from "react";
import "./App.css";

const detectedCards = [
  { card: "2H", confidence: 98 },
  { card: "8S", confidence: 80 },
  { card: "KD", confidence: 99 },
];

const allCards = [
  "A", "2", "3", "4", "5", "6", "7",
  "8", "9", "10", "J", "Q", "K",
];

const suits = [
  { symbol: "♥", name: "Hearts", color: "text-red-500" },
  { symbol: "♦", name: "Diamonds", color: "text-red-500" },
  { symbol: "♠", name: "Spades", color: "text-black" },
  { symbol: "♣", name: "Clubs", color: "text-black" },
];

function App() {
  const [count, setCount] = useState(0);
  const [connected, setConnected] = useState(true);

  const toggleConnection = () => {
    setConnected((prev) => !prev);
  };

  const resetCount = () => {
    setCount(0);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-wide">
              RAIN MAN <span className="text-yellow-400">2.0</span>
            </h1>
            <p className="text-sm text-slate-400">
              AI Card Detection & Counting
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  connected ? "bg-green-400" : "bg-red-400"
                }`}
              ></span>

              {connected ? "Camera Connected" : "Disconnected"}
            </div>

            <button
              onClick={toggleConnection}
              className="rounded-lg bg-slate-700 px-3 py-2 text-sm transition hover:bg-slate-600"
            >
              {connected ? "Disconnect" : "Connect"}
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-3">
          
          {/* Video Section */}
          <section className="lg:col-span-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold">Live Camera Feed</h2>

                <span className="rounded-md bg-green-500/10 px-2 py-1 text-xs text-green-400">
                  LIVE
                </span>
              </div>

              {/* Video placeholder */}
              <div className="video-placeholder relative flex aspect-video items-center justify-center overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
                <div className="text-center">
                  <div className="mb-3 text-5xl">📷</div>

                  <p className="text-slate-300">
                    Camera feed will appear here
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    WebRTC stream
                  </p>
                </div>

                {/* Detection boxes - mock */}
                <div className="absolute left-[15%] top-[30%] h-24 w-16 rounded border-2 border-green-400">
                  <span className="absolute -top-6 left-0 whitespace-nowrap bg-green-500 px-1.5 py-0.5 text-xs text-black">
                    2H 98%
                  </span>
                </div>

                <div className="absolute left-[42%] top-[25%] h-28 w-20 rounded border-2 border-green-400">
                  <span className="absolute -top-6 left-0 whitespace-nowrap bg-green-500 px-1.5 py-0.5 text-xs text-black">
                    8S 80%
                  </span>
                </div>

                <div className="absolute right-[20%] top-[35%] h-28 w-20 rounded border-2 border-green-400">
                  <span className="absolute -top-6 left-0 whitespace-nowrap bg-green-500 px-1.5 py-0.5 text-xs text-black">
                    KD 99%
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* Statistics */}
          <section className="space-y-4">
            <StatCard title="Running Count" value={count} />
            <StatCard title="Cards Detected" value={detectedCards.length} />
            <StatCard title="Cards Remaining" value={49} />
            <StatCard title="True Count" value={(count / 2).toFixed(1)} />

            <button
              onClick={resetCount}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 py-2.5 text-sm transition hover:bg-slate-700"
            >
              Reset Count
            </button>
          </section>
        </div>

        {/* Detected Cards */}
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-semibold">Detected Cards</h2>
              <p className="text-xs text-slate-500">
                Current frame detections
              </p>
            </div>

            <span className="text-sm text-slate-400">
              {detectedCards.length} cards
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
            {detectedCards.map((item) => (
              <div
                key={item.card}
                className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-center"
              >
                <div className="text-xl font-bold">{item.card}</div>

                <div className="mt-1 text-xs text-green-400">
                  {item.confidence}% confidence
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Card Status */}
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-4 font-semibold">Deck Status</h2>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {suits.map((suit) => (
              <div key={suit.name}>
                <div className="mb-2 flex items-center gap-2 text-sm text-slate-400">
                  <span className={`text-xl ${suit.color}`}>
                    {suit.symbol}
                  </span>
                  {suit.name}
                </div>

                <div className="grid grid-cols-7 gap-1">
                  {allCards.map((card) => {
                    const used =
                      (card === "2" && suit.name === "Hearts") ||
                      (card === "8" && suit.name === "Spades") ||
                      (card === "K" && suit.name === "Diamonds");

                    return (
                      <div
                        key={`${suit.name}-${card}`}
                        className={`rounded border p-1 text-center text-xs ${
                          used
                            ? "border-yellow-500 bg-yellow-500/20 text-yellow-300"
                            : "border-slate-700 bg-slate-800 text-slate-400"
                        }`}
                      >
                        {card}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Detection Log */}
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold">Detection Log</h2>

          <div className="space-y-2 text-sm">
            {detectedCards.map((item, index) => (
              <div
                key={`${item.card}-${index}`}
                className="flex items-center justify-between rounded bg-slate-800 px-3 py-2"
              >
                <span>
                  Detected <strong>{item.card}</strong>
                </span>

                <span className="text-green-400">
                  {item.confidence}%
                </span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="mt-1 text-3xl font-bold text-yellow-400">{value}</p>
    </div>
  );
}

export default App;