"use client";

import { useEffect, useRef, useState } from "react";

type Request = { expected: string; description: string; resolve: (value: string | null) => void };

export function TypedConfirmation({ expected, description, onClose }: {
  expected: string; description: string; onClose: (value: string | null) => void;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return (
    <dialog ref={ref} aria-labelledby="confirmation-title" onCancel={(event) => {
      event.preventDefault(); onClose(null);
    }} className="w-full max-w-lg rounded-xl border border-border bg-background p-6 text-foreground shadow-xl backdrop:bg-black/50">
      <form onSubmit={(event) => { event.preventDefault(); if (value === expected) onClose(value); }}>
        <h2 id="confirmation-title" className="text-lg font-semibold">Confirm action</h2>
        <p className="mt-3 text-sm">{description}</p>
        <label htmlFor="confirmation-value" className="mt-4 block text-sm">Type exactly:</label>
        <code className="my-2 block break-all rounded bg-muted p-2">{expected}</code>
        <input id="confirmation-value" autoFocus autoComplete="off" spellCheck={false} value={value}
          onChange={(event) => setValue(event.target.value)}
          className="w-full rounded border border-border bg-background p-2" />
        <div className="mt-5 flex justify-end gap-3">
          <button type="button" onClick={() => onClose(null)} className="rounded border border-border px-4 py-2">Cancel</button>
          <button type="submit" disabled={value !== expected}
            className="rounded bg-primary px-4 py-2 text-primary-foreground disabled:cursor-not-allowed disabled:opacity-40">Confirm</button>
        </div>
      </form>
    </dialog>
  );
}

export function useTypedConfirmation() {
  const [request, setRequest] = useState<Request | null>(null);
  const pending = useRef<Request | null>(null);
  useEffect(() => () => { pending.current?.resolve(null); }, []);
  function confirm(expected: string, description: string): Promise<string | null> {
    pending.current?.resolve(null);
    return new Promise((resolve) => {
      const next = { expected, description, resolve };
      pending.current = next;
      setRequest(next);
    });
  }
  const dialog = request ? <TypedConfirmation key={request.expected} expected={request.expected} description={request.description}
    onClose={(value) => { request.resolve(value); pending.current = null; setRequest(null); }} /> : null;
  return { confirm, dialog };
}
