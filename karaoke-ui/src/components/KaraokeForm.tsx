"use client";

import { useState } from "react";

interface KaraokeFormProps {
  onSubmit: (formData: { youtubeUrl: string; track?: string; artist?: string }) => void;
  isProcessing: boolean;
}

export default function KaraokeForm({ onSubmit, isProcessing }: KaraokeFormProps) {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [track, setTrack] = useState("");
  const [artist, setArtist] = useState("");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    onSubmit({ youtubeUrl, track: track.trim() || undefined, artist: artist.trim() || undefined });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="youtubeUrl"
          className="block text-sm font-medium text-gray-300"
        >
          YouTube URL
        </label>
        <input
          type="text"
          id="youtubeUrl"
          value={youtubeUrl}
          onChange={(e) => setYoutubeUrl(e.target.value)}
          className="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white p-2"
          placeholder="https://www.youtube.com/watch?v=..."
          required
        />
      </div>
      <div>
        <label htmlFor="track" className="block text-sm font-medium text-gray-300">
          Track (optional)
        </label>
        <input
          type="text"
          id="track"
          value={track}
          onChange={(e) => setTrack(e.target.value)}
          className="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white p-2"
          placeholder="Song title"
        />
      </div>
      <div>
        <label htmlFor="artist" className="block text-sm font-medium text-gray-300">
          Artist (optional)
        </label>
        <input
          type="text"
          id="artist"
          value={artist}
          onChange={(e) => setArtist(e.target.value)}
          className="mt-1 block w-full rounded-md bg-gray-700 border-gray-600 text-white p-2"
          placeholder="Artist name"
        />
      </div>
      <button
        type="submit"
        disabled={isProcessing}
        className="w-full px-4 py-2 font-bold text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-500 disabled:cursor-not-allowed"
      >
        {isProcessing ? "Generating..." : "Create Karaoke Video"}
      </button>
    </form>
  );
} 