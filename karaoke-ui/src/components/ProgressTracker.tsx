"use client";

import { CheckCircle, Loader, XCircle } from "lucide-react";

export interface StatusMessage {
  event: string;
  message: string;
  data?: any;
}

interface ProgressTrackerProps {
  messages: StatusMessage[];
  isProcessing: boolean;
}

export default function ProgressTracker({ messages }: ProgressTrackerProps) {
  if (messages.length === 0) return null;

  return (
    <div className="mt-8 p-4 bg-gray-800 rounded-lg">
      <h2 className="text-lg font-semibold mb-4">Progress</h2>
      <ul className="space-y-3">
        {messages.map((msg, index) => {
          const isDone = msg.event.endsWith(":done") || msg.event === "done";
          const isError = msg.event.endsWith(":error") || msg.event === "error";

          return (
            <li key={index} className="flex items-center space-x-3">
              {isError ? (
                <XCircle className="h-5 w-5 text-red-500" />
              ) : isDone ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <Loader className="h-5 w-5 text-blue-500 animate-spin" />
              )}
              <span>{msg.message}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
} 