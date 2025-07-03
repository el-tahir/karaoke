"use client";

import { useState } from "react";
import KaraokeForm from "@/components/KaraokeForm";
import ProgressTracker, { StatusMessage } from "@/components/ProgressTracker";
import ResultsDisplay from "@/components/ResultsDisplay";

export default function HomePage() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<StatusMessage[]>([]);
  const [results, setResults] = useState<{ karaokeUrl?: string; fullSongUrl?: string }>({});

  const handleFormSubmit = ({ youtubeUrl, track, artist }: { youtubeUrl: string; track?: string; artist?: string }) => {
    setIsProcessing(true);
    setMessages([]);
    setResults({});

    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const url = new URL(`${apiBase}/generate-karaoke`);
    url.searchParams.append("youtube_url", youtubeUrl);
    if (track) url.searchParams.append("track", track);
    if (artist) url.searchParams.append("artist", artist);

    const eventSource = new EventSource(url.toString());

    eventSource.onmessage = (event) => {
      const status: StatusMessage = JSON.parse(event.data);

      setMessages((prev) => {
        const root = status.event.split(":"[0]);
        return [...prev, status];
      });

      if (status.event === "done") {
        setResults({
          karaokeUrl: status.data?.karaoke_video_url,
          fullSongUrl: status.data?.full_song_video_url,
        });
        setIsProcessing(false);
        eventSource.close();
      }

      if (status.event === "error") {
        setIsProcessing(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setMessages((prev) => [
        ...prev,
        { event: "error", message: "A connection error occurred." },
      ]);
      setIsProcessing(false);
      eventSource.close();
    };
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gray-900 text-white">
      <div className="w-full max-w-2xl">
        <h1 className="text-4xl font-bold text-center mb-2">AI Karaoke Video Generator</h1>
        <p className="text-center text-gray-400 mb-8">
          Enter a YouTube URL and let the magic happen.
        </p>

        {!results.karaokeUrl && (
          <KaraokeForm onSubmit={handleFormSubmit} isProcessing={isProcessing} />
        )}

        <ProgressTracker messages={messages} isProcessing={isProcessing} />

        <ResultsDisplay
          karaokeUrl={results.karaokeUrl}
          fullSongUrl={results.fullSongUrl}
        />

        {results.karaokeUrl && (
          <button
            onClick={() => {
              setResults({});
              setMessages([]);
            }}
            className="mt-8 w-full px-4 py-2 font-bold text-white bg-gray-600 rounded-md hover:bg-gray-700"
          >
            Create Another
          </button>
        )}
      </div>
    </main>
  );
}
