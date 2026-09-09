import { useEffect, useRef, useState } from "react";
import "./App.css";

// ==================================================
// CARD RANKS
// ==================================================

const allCards = [
  "A",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "J",
  "Q",
  "K",
];

// ==================================================
// SUITS
// ==================================================

const suits = [
  {
    symbol: "♥",
    name: "Hearts",
    color: "text-red-500",
    code: "H",
  },
  {
    symbol: "♦",
    name: "Diamonds",
    color: "text-red-500",
    code: "D",
  },
  {
    symbol: "♠",
    name: "Spades",
    color: "text-white",
    code: "S",
  },
  {
    symbol: "♣",
    name: "Clubs",
    color: "text-white",
    code: "C",
  },
];

// ==================================================
// NORMALIZE CARD NAME
// ==================================================

function normalizeCard(cardName) {
  if (!cardName) {
    return null;
  }

  return String(cardName)
    .trim()
    .toUpperCase();
}

// ==================================================
// CHECK WHETHER CARD HAS BEEN COUNTED
// ==================================================

function isCardCounted(
  cardName,
  suitCode,
  countedCards
) {
  const target =
    `${cardName}${suitCode}`.toUpperCase();

  return countedCards.some((item) => {
    const normalized =
      normalizeCard(item);

    return normalized === target;
  });
}

// ==================================================
// APP
// ==================================================

function App() {
  const socketRef = useRef(null);
  const fileInputRef = useRef(null);

  // ==================================================
  // DATA
  // ==================================================

  const [data, setData] = useState({
    cards: [],

    // Current running count
    running_count: 0,

    // Number of unique cards permanently counted
    cards_counted: 0,

    // Remaining cards in deck
    cards_remaining: 52,

    // True count
    true_count: 0,

    // Array of unique card names already counted
    counted_cards: [],
  });

  // ==================================================
  // CONNECTION
  // ==================================================

  const [connected, setConnected] =
    useState(false);

  // ==================================================
  // VIDEO
  // ==================================================

  const [videoFrame, setVideoFrame] =
    useState(null);

  const [videoId, setVideoId] =
    useState(null);

  const [videoName, setVideoName] =
    useState("");

  const [playing, setPlaying] =
    useState(false);

  const [ended, setEnded] =
    useState(false);

  const [position, setPosition] =
    useState(0);

  const [duration, setDuration] =
    useState(0);

  // ==================================================
  // PROCESSED FRAME SIZE
  // ==================================================

  const [frameWidth, setFrameWidth] =
    useState(640);

  const [frameHeight, setFrameHeight] =
    useState(360);

  // ==================================================
  // PLAYBACK SPEED
  // ==================================================

  const [speed, setSpeed] =
    useState(1);

  // ==================================================
  // CONFIDENCE
  // ==================================================

  const [confidenceThreshold, setConfidenceThreshold] =
    useState(0.70);

  // ==================================================
  // FPS
  // ==================================================

  const [fps, setFps] =
    useState(0);

  const frameTimesRef =
    useRef([]);

  // ==================================================
  // REAL-TIME FPS
  // ==================================================

  const updateFPS = () => {
    const now =
      performance.now();

    frameTimesRef.current.push(
      now
    );

    frameTimesRef.current =
      frameTimesRef.current.filter(
        (time) =>
          now - time < 1000
      );

    setFps(
      frameTimesRef.current.length
    );
  };

  // ==================================================
  // SEND COMMAND
  // ==================================================

  const sendCommand = (command) => {
    const socket =
      socketRef.current;

    if (
      socket &&
      socket.readyState ===
        WebSocket.OPEN
    ) {
      socket.send(
        JSON.stringify(command)
      );
    }
  };

  // ==================================================
  // RESET FRONTEND DATA
  // ==================================================

  const resetData = () => {
    setData({
      cards: [],
      running_count: 0,
      cards_counted: 0,
      cards_remaining: 52,
      true_count: 0,
      counted_cards: [],
    });
  };

  // ==================================================
  // FILE SELECTION
  // ==================================================

  const handleFileSelect = async (
    event
  ) => {
    const file =
      event.target.files?.[0];

    if (!file) {
      return;
    }

    console.log(
      "Selected video:",
      file.name
    );

    // ==================================================
    // CLOSE PREVIOUS SOCKET
    // ==================================================

    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    // ==================================================
    // RESET UI
    // ==================================================

    setConnected(false);
    setPlaying(false);
    setEnded(false);

    setVideoFrame(null);

    setVideoId(null);
    setVideoName("");

    setPosition(0);
    setDuration(0);

    setFrameWidth(640);
    setFrameHeight(360);

    setFps(0);

    frameTimesRef.current = [];

    resetData();

    try {
      // ==================================================
      // UPLOAD
      // ==================================================

      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const response =
        await fetch(
          "http://127.0.0.1:8000/upload-video",
          {
            method: "POST",
            body: formData,
          }
        );

      if (!response.ok) {
        throw new Error(
          `Upload failed with status ${response.status}`
        );
      }

      const result =
        await response.json();

      if (
        result.status !== "ok"
      ) {
        alert(
          result.message ||
            "Video upload failed"
        );

        return;
      }

      setVideoId(
        result.video_id
      );

      setVideoName(
        file.name
      );

      // ==================================================
      // CONNECT WEBSOCKET
      // ==================================================

      const socket =
        new WebSocket(
          "ws://127.0.0.1:8000/ws"
        );

      socketRef.current =
        socket;

      // ==================================================
      // SOCKET OPEN
      // ==================================================

      socket.onopen = () => {
        console.log(
          "WebSocket connected"
        );

        setConnected(true);

        socket.send(
          JSON.stringify({
            action: "load",
            video_id:
              result.video_id,
          })
        );
      };

      // ==================================================
      // SOCKET MESSAGE
      // ==================================================

      socket.onmessage = (
        event
      ) => {
        try {
          const receivedData =
            JSON.parse(
              event.data
            );

          // ==================================================
          // BACKEND ERROR
          // ==================================================

          if (
            receivedData.type ===
            "error"
          ) {
            console.error(
              "Backend error:",
              receivedData.message
            );

            return;
          }

          // ==================================================
          // IGNORE UNKNOWN MESSAGE
          // ==================================================

          if (
            receivedData.type !==
            "frame"
          ) {
            return;
          }

          // ==================================================
          // VIDEO ENDED
          // ==================================================

          if (
            receivedData.ended
          ) {
            setPlaying(false);
            setEnded(true);
          }

          // ==================================================
          // FRAME
          // ==================================================

          if (
            receivedData.frame
          ) {
            updateFPS();

            setVideoFrame(
              `data:image/jpeg;base64,${receivedData.frame}`
            );
          }

          // ==================================================
          // FRAME DIMENSIONS
          // ==================================================

          if (
            receivedData.frame_width
          ) {
            setFrameWidth(
              receivedData.frame_width
            );
          }

          if (
            receivedData.frame_height
          ) {
            setFrameHeight(
              receivedData.frame_height
            );
          }

          // ==================================================
          // ALL DETECTION + COUNTING DATA
          // ==================================================

          setData({
            // Currently visible tracked cards
            cards:
              receivedData.cards ||
              [],

            // Hi-Lo running count
            running_count:
              receivedData.running_count ??
              0,

            // Number of unique cards counted
            cards_counted:
              receivedData.cards_counted ??
              0,

            // Cards remaining in deck
            cards_remaining:
              receivedData.cards_remaining ??
              52,

            // True count
            true_count:
              receivedData.true_count ??
              0,

            // Permanently counted cards
            counted_cards:
              receivedData.counted_cards ||
              [],
          });

          // ==================================================
          // POSITION
          // ==================================================

          if (
            receivedData.position !==
            undefined
          ) {
            setPosition(
              receivedData.position
            );
          }

          // ==================================================
          // DURATION
          // ==================================================

          if (
            receivedData.duration !==
            undefined
          ) {
            setDuration(
              receivedData.duration
            );
          }

          // ==================================================
          // PLAYING STATE
          // ==================================================

          if (
            receivedData.playing !==
              undefined &&
            !receivedData.ended
          ) {
            setPlaying(
              receivedData.playing
            );
          }

        } catch (error) {
          console.error(
            "WebSocket message error:",
            error
          );
        }
      };

      // ==================================================
      // SOCKET CLOSE
      // ==================================================

      socket.onclose = () => {
        console.log(
          "WebSocket disconnected"
        );

        setConnected(false);
        setPlaying(false);
      };

      // ==================================================
      // SOCKET ERROR
      // ==================================================

      socket.onerror = (
        error
      ) => {
        console.error(
          "WebSocket error:",
          error
        );

        setConnected(false);
      };

    } catch (error) {
      console.error(
        "Upload error:",
        error
      );

      alert(
        "Could not upload video. Make sure FastAPI is running."
      );
    }
  };

  // ==================================================
  // PLAY / PAUSE / RESTART
  // ==================================================

  const togglePlay = () => {

    // ==================================================
    // RESTART
    // ==================================================

    if (ended) {

      sendCommand({
        action: "seek",
        position: 0,
      });

      setPosition(0);
      setEnded(false);

      resetData();

      setTimeout(() => {

        sendCommand({
          action: "play",
        });

        setPlaying(true);

      }, 100);

      return;
    }

    // ==================================================
    // PAUSE
    // ==================================================

    if (playing) {

      sendCommand({
        action: "pause",
      });

      setPlaying(false);

      return;
    }

    // ==================================================
    // PLAY
    // ==================================================

    sendCommand({
      action: "play",
    });

    setPlaying(true);
  };

  // ==================================================
  // SEEK
  // ==================================================

  const handleSeek = (
    event
  ) => {

    const newPosition =
      Number(
        event.target.value
      );

    setPosition(
      newPosition
    );

    if (
      newPosition <
      duration
    ) {
      setEnded(false);
    }

    // Seeking represents a new analysis
    resetData();

    sendCommand({
      action: "seek",
      position:
        newPosition,
    });
  };

  // ==================================================
  // BACKWARD 5 SEC
  // ==================================================

  const backward = () => {

    setEnded(false);

    resetData();

    sendCommand({
      action: "backward",
    });
  };

  // ==================================================
  // FORWARD 5 SEC
  // ==================================================

  const forward = () => {

    setEnded(false);

    resetData();

    sendCommand({
      action: "forward",
    });
  };

  // ==================================================
  // SPEED
  // ==================================================

  const changeSpeed = (
    newSpeed
  ) => {

    setSpeed(
      newSpeed
    );

    sendCommand({
      action: "speed",
      value:
        newSpeed,
    });
  };

  // ==================================================
  // CONFIDENCE
  // ==================================================

  const changeConfidence = (
    event
  ) => {

    const value =
      Number(
        event.target.value
      );

    setConfidenceThreshold(
      value
    );

    sendCommand({
      action: "threshold",
      value,
    });
  };

  // ==================================================
  // CLEANUP
  // ==================================================

  useEffect(() => {

    return () => {

      if (
        socketRef.current
      ) {
        socketRef.current.close();
      }

    };

  }, []);

  // ==================================================
  // FORMAT TIME
  // ==================================================

  const formatTime = (
    seconds
  ) => {

    if (
      !seconds ||
      !Number.isFinite(
        seconds
      )
    ) {
      return "00:00";
    }

    const mins =
      Math.floor(
        seconds / 60
      );

    const secs =
      Math.floor(
        seconds % 60
      );

    return (
      `${String(mins).padStart(
        2,
        "0"
      )}:` +
      `${String(secs).padStart(
        2,
        "0"
      )}`
    );
  };

  // ==================================================
  // RENDER
  // ==================================================

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* ==================================================
          HEADER
      ================================================== */}

      <header className="border-b border-slate-800 bg-slate-900">

        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">

          <div>

            <h1 className="text-2xl font-bold tracking-wide">

              RAIN MAN{" "}

              <span className="text-yellow-400">
                2.0
              </span>

            </h1>

            <p className="text-sm text-slate-400">
              AI Card Detection & Counting
            </p>

          </div>

          {/* CONNECTION STATUS */}

          <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm">

            <span
              className={`h-2.5 w-2.5 rounded-full ${
                connected
                  ? "bg-green-400"
                  : "bg-red-400"
              }`}
            />

            {connected
              ? "Backend Connected"
              : "Backend Disconnected"}

          </div>

        </div>

      </header>

      {/* ==================================================
          MAIN
      ================================================== */}

      <main className="mx-auto max-w-7xl px-4 py-6">

        {/* ==================================================
            VIDEO CONTROLS
        ================================================== */}

        <section className="mb-6 rounded-xl border border-slate-800 bg-slate-900 p-4">

          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

            {/* FILE PICKER */}

            <div>

              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={
                  handleFileSelect
                }
                className="hidden"
              />

              <button
                onClick={() =>
                  fileInputRef.current?.click()
                }
                className="cursor-pointer rounded-lg bg-yellow-400 px-4 py-2 font-semibold text-black hover:bg-yellow-300"
              >
                📂 Choose Video
              </button>

              <span className="ml-3 text-sm text-slate-400">
                {videoName ||
                  "No video selected"}
              </span>

            </div>

            {/* FPS */}

            <div className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2">

              <span className="text-sm text-slate-400">
                Live FPS
              </span>

              <span className="ml-2 font-bold text-green-400">
                {fps}
              </span>

            </div>

            {/* CONFIDENCE */}

            <div className="min-w-[260px]">

              <div className="mb-1 flex justify-between text-sm">

                <span className="text-slate-400">
                  Confidence
                </span>

                <span className="font-semibold text-yellow-400">
                  {Math.round(
                    confidenceThreshold *
                      100
                  )}
                  %
                </span>

              </div>

              <input
                type="range"
                min="0.10"
                max="0.95"
                step="0.05"
                value={
                  confidenceThreshold
                }
                onChange={
                  changeConfidence
                }
                className="w-full cursor-pointer"
              />

            </div>

          </div>

        </section>

        {/* ==================================================
            VIDEO + STATISTICS
        ================================================== */}

        <div className="grid gap-6 lg:grid-cols-3">

          {/* ==================================================
              VIDEO
          ================================================== */}

          <section className="lg:col-span-2">

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

              {/* VIDEO HEADER */}

              <div className="mb-3 flex items-center justify-between">

                <h2 className="font-semibold">
                  Live Camera Feed
                </h2>

                <span className="rounded-md bg-green-500/10 px-2 py-1 text-xs text-green-400">

                  {playing
                    ? "PLAYING"
                    : ended
                    ? "ENDED"
                    : "PAUSED"}

                </span>

              </div>

              {/* ==================================================
                  VIDEO CONTAINER
              ================================================== */}

              <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-lg border border-slate-700 bg-black">

                {videoFrame ? (

                  <div
                    className="relative max-h-full max-w-full"
                    style={{
                      aspectRatio:
                        `${frameWidth} / ${frameHeight}`,

                      height:
                        frameHeight >
                        frameWidth
                          ? "100%"
                          : "auto",

                      width:
                        frameWidth >=
                        frameHeight
                          ? "100%"
                          : "auto",
                    }}
                  >

                    {/* VIDEO IMAGE */}

                    <img
                      src={videoFrame}
                      alt="Selected video"
                      className="absolute inset-0 h-full w-full object-fill"
                    />

                    {/* ==================================================
                        REAL YOLO / TRACKER BOXES
                    ================================================== */}

                    {data.cards.map(
                      (card, index) => {

                        const bbox =
                          card.bbox ||
                          card.box ||
                          [
                            card.x1,
                            card.y1,
                            card.x2,
                            card.y2,
                          ];

                        if (
                          !bbox ||
                          bbox.length !== 4 ||
                          bbox.some(
                            (value) =>
                              value ===
                                undefined ||
                              value ===
                                null
                          )
                        ) {
                          return null;
                        }

                        const boxFrameWidth =
                          Number(
                            card.frame_width ||
                              frameWidth
                          );

                        const boxFrameHeight =
                          Number(
                            card.frame_height ||
                              frameHeight
                          );

                        if (
                          boxFrameWidth <= 0 ||
                          boxFrameHeight <= 0
                        ) {
                          return null;
                        }

                        const left =
                          (Number(
                            bbox[0]
                          ) /
                            boxFrameWidth) *
                          100;

                        const top =
                          (Number(
                            bbox[1]
                          ) /
                            boxFrameHeight) *
                          100;

                        const width =
                          ((Number(
                            bbox[2]
                          ) -
                            Number(
                              bbox[0]
                            )) /
                            boxFrameWidth) *
                          100;

                        const height =
                          ((Number(
                            bbox[3]
                          ) -
                            Number(
                              bbox[1]
                            )) /
                            boxFrameHeight) *
                          100;

                        const confidence =
                          Number(
                            card.confidence ||
                              0
                          );

                        const confidencePercent =
                          Math.round(
                            confidence <= 1
                              ? confidence *
                                  100
                              : confidence
                          );

                        return (
                          <div
                            key={`${card.track_id ?? "track"}-${card.card}-${index}`}
                            className="pointer-events-none absolute border-2 border-green-400"
                            style={{
                              left:
                                `${left}%`,
                              top:
                                `${top}%`,
                              width:
                                `${width}%`,
                              height:
                                `${height}%`,
                            }}
                          >

                            <span className="absolute -top-6 left-0 whitespace-nowrap rounded bg-green-400 px-1.5 py-0.5 text-xs font-semibold text-black">

                              {card.card}{" "}

                              {confidencePercent}%

                              {card.track_id !==
                                undefined &&
                                ` #${card.track_id}`}

                            </span>

                          </div>
                        );
                      }
                    )}

                  </div>

                ) : (

                  <div className="flex h-full items-center justify-center text-slate-400">
                    Choose a video to begin
                  </div>

                )}

              </div>

              {/* ==================================================
                  PLAYBACK CONTROLS
              ================================================== */}

              <div className="mt-4">

                {/* SEEK BAR */}

                <input
                  type="range"
                  min="0"
                  max={
                    duration || 1
                  }
                  step="0.1"
                  value={Math.min(
                    position,
                    duration || 1
                  )}
                  onChange={
                    handleSeek
                  }
                  className="w-full cursor-pointer"
                />

                {/* TIME */}

                <div className="mt-1 flex justify-between text-xs text-slate-500">

                  <span>
                    {formatTime(
                      position
                    )}
                  </span>

                  <span>
                    {formatTime(
                      duration
                    )}
                  </span>

                </div>

                {/* BUTTONS */}

                <div className="mt-3 flex flex-wrap items-center justify-center gap-2">

                  {/* BACKWARD */}

                  <button
                    onClick={
                      backward
                    }
                    className="cursor-pointer rounded-lg bg-slate-800 px-4 py-2 hover:bg-slate-700"
                  >
                    ⏪ 5s
                  </button>

                  {/* PLAY / PAUSE / RESTART */}

                  <button
                    onClick={
                      togglePlay
                    }
                    className="cursor-pointer rounded-lg bg-yellow-400 px-6 py-2 font-bold text-black hover:bg-yellow-300"
                  >

                    {ended
                      ? "↻ Restart"
                      : playing
                      ? "⏸ Pause"
                      : "▶ Play"}

                  </button>

                  {/* FORWARD */}

                  <button
                    onClick={
                      forward
                    }
                    className="cursor-pointer rounded-lg bg-slate-800 px-4 py-2 hover:bg-slate-700"
                  >
                    5s ⏩
                  </button>

                  {/* SPEED */}

                  <select
                    value={speed}
                    onChange={(event) =>
                      changeSpeed(
                        Number(
                          event.target.value
                        )
                      )
                    }
                    className="cursor-pointer rounded-lg bg-slate-800 px-3 py-2 text-white"
                  >

                    <option value="0.5">
                      0.5×
                    </option>

                    <option value="1">
                      1×
                    </option>

                    <option value="1.5">
                      1.5×
                    </option>

                    <option value="2">
                      2×
                    </option>

                  </select>

                </div>

              </div>

            </div>

          </section>

          {/* ==================================================
              STATISTICS
          ================================================== */}

          <section className="space-y-4">

            <StatCard
              title="Running Count"
              value={
                data.running_count
              }
            />

            <StatCard
              title="Cards Counted"
              value={
                data.cards_counted
              }
            />

            <StatCard
              title="Cards Remaining"
              value={
                data.cards_remaining
              }
            />

            <StatCard
              title="True Count"
              value={
                data.true_count
              }
            />

          </section>

        </div>

        {/* ==================================================
            CURRENTLY DETECTED CARDS
        ================================================== */}

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">

          <div className="mb-4 flex items-center justify-between">

            <div>

              <h2 className="font-semibold">
                Detected Cards
              </h2>

              <p className="text-xs text-slate-500">
                Currently tracked by YOLO
              </p>

            </div>

            <span className="text-sm text-slate-400">
              {data.cards.length} visible
            </span>

          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">

            {data.cards.map(
              (item, index) => (

                <div
                  key={`${item.track_id ?? "track"}-${item.card}-${index}`}
                  className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-center"
                >

                  <div className="text-xl font-bold">
                    {item.card}
                  </div>

                  <div className="mt-1 text-xs text-green-400">

                    {Math.round(
                      item.confidence <= 1
                        ? item.confidence *
                            100
                        : item.confidence
                    )}

                    % confidence

                  </div>

                  {item.track_id !==
                    undefined && (

                    <div className="mt-1 text-xs text-slate-500">
                      Track #
                      {item.track_id}
                    </div>

                  )}

                </div>

              )
            )}

          </div>

        </section>

        {/* ==================================================
            DECK STATUS
        ================================================== */}

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">

          <div className="mb-4 flex items-center justify-between">

            <div>

              <h2 className="font-semibold">
                Deck Status
              </h2>

              <p className="text-xs text-slate-500">
                Cards already counted are shaded and crossed out
              </p>

            </div>

            <span className="text-xs text-slate-500">

              {data.cards_counted}
              /52 counted

            </span>

          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">

            {suits.map(
              (suit) => (

                <div
                  key={suit.name}
                >

                  {/* SUIT HEADER */}

                  <div className="mb-2 flex items-center gap-2 text-sm text-slate-400">

                    <span
                      className={`text-xl ${suit.color}`}
                    >
                      {suit.symbol}
                    </span>

                    {suit.name}

                  </div>

                  {/* CARD GRID */}

                  <div className="grid grid-cols-7 gap-1">

                    {allCards.map(
                      (card) => {

                        // IMPORTANT:
                        //
                        // Use counted_cards,
                        // NOT data.cards.
                        //
                        // data.cards = currently visible
                        // counted_cards = permanently counted

                        const counted =
                          isCardCounted(
                            card,
                            suit.code,
                            data.counted_cards
                          );

                        return (

                          <div
                            key={`${suit.name}-${card}`}
                            className={`rounded border p-1 text-center text-xs transition-all ${
                              counted
                                ? "border-yellow-400 bg-yellow-400/30 text-yellow-200 line-through opacity-80"
                                : "border-slate-700 bg-slate-800 text-slate-400"
                            }`}
                          >
                            {card}
                          </div>

                        );

                      }
                    )}

                  </div>

                </div>

              )
            )}

          </div>

        </section>

        {/* ==================================================
            COUNTED CARDS
        ================================================== */}

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">

          <div className="mb-4 flex items-center justify-between">

            <div>

              <h2 className="font-semibold">
                Counted Cards
              </h2>

              <p className="text-xs text-slate-500">
                Unique cards that have contributed to the running count
              </p>

            </div>

            <span className="text-sm text-slate-400">
              {data.counted_cards.length}
              /52
            </span>

          </div>

          {data.counted_cards.length ===
          0 ? (

            <p className="text-sm text-slate-500">
              No cards counted yet.
            </p>

          ) : (

            <div className="flex flex-wrap gap-2">

              {data.counted_cards.map(
                (card) => (

                  <span
                    key={card}
                    className="rounded-md border border-yellow-400/40 bg-yellow-400/10 px-3 py-1 text-sm font-semibold text-yellow-300"
                  >
                    {card}
                  </span>

                )
              )}

            </div>

          )}

        </section>

        {/* ==================================================
            DETECTION LOG
        ================================================== */}

        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4">

          <div className="mb-3 flex items-center justify-between">

            <h2 className="font-semibold">
              Detection Log
            </h2>

            <span className="text-xs text-slate-500">
              Current tracked detections
            </span>

          </div>

          <div className="space-y-2">

            {data.cards.length ===
            0 ? (

              <p className="text-sm text-slate-500">
                No cards currently detected.
              </p>

            ) : (

              data.cards.map(
                (item, index) => (

                  <div
                    key={`${item.track_id ?? "track"}-${item.card}-${index}`}
                    className="flex items-center justify-between rounded bg-slate-800 px-3 py-2 text-sm"
                  >

                    <span>

                      Detected{" "}

                      <strong>
                        {item.card}
                      </strong>

                      {item.track_id !==
                        undefined && (

                        <span className="ml-2 text-xs text-slate-500">
                          Track #
                          {item.track_id}
                        </span>

                      )}

                    </span>

                    <span className="text-green-400">

                      {Math.round(
                        item.confidence <=
                          1
                          ? item.confidence *
                              100
                          : item.confidence
                      )}

                      %

                    </span>

                  </div>

                )
              )

            )}

          </div>

        </section>

      </main>

    </div>
  );
}

// ==================================================
// STAT CARD
// ==================================================

function StatCard({
  title,
  value,
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">

      <p className="text-sm text-slate-400">
        {title}
      </p>

      <p className="mt-1 text-3xl font-bold text-yellow-400">
        {value}
      </p>

    </div>
  );
}

export default App;