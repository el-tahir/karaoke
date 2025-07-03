"use client";

interface ResultsDisplayProps {
  karaokeUrl?: string;
  fullSongUrl?: string;
}

export default function ResultsDisplay({ karaokeUrl, fullSongUrl }: ResultsDisplayProps) {
  if (!karaokeUrl) return null;

  return (
    <div className="mt-8 p-4 bg-green-900/50 border border-green-500 rounded-lg">
      <h2 className="text-xl font-bold text-green-300 mb-4">Done! Download Your Videos:</h2>
      <div className="space-y-3">
        {karaokeUrl && (
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${karaokeUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center px-4 py-2 font-bold text-white bg-green-600 rounded-md hover:bg-green-700"
          >
            Download Karaoke Video (Instrumental)
          </a>
        )}
        {fullSongUrl && (
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}${fullSongUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center px-4 py-2 font-bold text-white bg-teal-600 rounded-md hover:bg-teal-700"
          >
            Download Full Song Video (with Vocals)
          </a>
        )}
      </div>
    </div>
  );
} 