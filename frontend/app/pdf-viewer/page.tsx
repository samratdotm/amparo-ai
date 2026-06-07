"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function PDFViewer() {
  const params = useSearchParams();
  const file = params.get("file") ?? "";
  const page = params.get("page") ?? "1";
  const source = params.get("source") ?? "";

  // Build the src with #page=N so Chrome's built-in viewer navigates there.
  // Using an iframe forces inline viewing even when the OS would otherwise
  // open PDFs in an external app (e.g. Preview on macOS).
  const src = `${file}#page=${page}`;

  if (!file) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-950 text-zinc-400">
        No file specified.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-950">
      {source && (
        <div className="flex items-center gap-3 px-4 py-2 bg-zinc-900 border-b border-zinc-800 text-sm text-zinc-400 flex-shrink-0">
          <span className="text-blue-400">📄</span>
          <span>{source}</span>
          <span className="ml-auto text-zinc-600">page {page}</span>
        </div>
      )}
      <iframe
        src={src}
        className="flex-1 w-full border-0"
        title={source || file}
      />
    </div>
  );
}

export default function PDFViewerPage() {
  return (
    <Suspense>
      <PDFViewer />
    </Suspense>
  );
}
