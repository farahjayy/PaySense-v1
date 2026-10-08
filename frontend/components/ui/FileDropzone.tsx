"use client";
import { useRef, useState } from "react";
import type { DragEvent } from "react";

type Props = {
  accept: string;
  hint: string;
  onFile: (file: File) => void;
  isDisabled?: boolean;
};

export function FileDropzone({ accept, hint, onFile, isDisabled = false }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setIsDragging(false);
    if (isDisabled) return;
    const file = event.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  return (
    <>
      <button
        type="button"
        disabled={isDisabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`flex w-full flex-col items-center gap-2 rounded-card border-2 border-dashed px-6 py-10 text-center transition-colors ${
          isDragging ? "border-accent bg-accent-bg" : "border-line bg-surface-2 hover:border-ink-muted"
        } ${isDisabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
      >
        <span className="text-2xl" aria-hidden>📄</span>
        <span className="text-[13px] font-semibold text-ink">
          Drop a file here or click to browse
        </span>
        <span className="text-[11px] text-ink-muted">{hint}</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </>
  );
}
