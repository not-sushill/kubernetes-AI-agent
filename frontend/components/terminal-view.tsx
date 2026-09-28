"use client";

import { forwardRef, useEffect, useLayoutEffect, useImperativeHandle, useRef } from "react";
import type { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";

export type TerminalHandle = {
  write: (value: string) => void;
  clear: () => void;
  focus: () => void;
  size: () => {rows: number; cols: number};
};

type Props = {
  enabled: boolean;
  onInput: (data: string) => void;
  onResize: (rows: number, cols: number) => void;
  onReady: () => void;
  onError: (message: string) => void;
};

export const TerminalView = forwardRef<TerminalHandle, Props>(function TerminalView(props, ref) {
  const element = useRef<HTMLDivElement>(null);
  const terminal = useRef<Terminal | null>(null);
  const callbacks = useRef(props);
  useLayoutEffect(() => { callbacks.current = props; });
  useImperativeHandle(ref, () => ({
    write: value => terminal.current?.write(value),
    clear: () => terminal.current?.reset(),
    focus: () => {
      if (terminal.current) {
        terminal.current.options.disableStdin = !callbacks.current.enabled;
        terminal.current.focus();
      }
    },
    size: () => ({rows: terminal.current?.rows || 24, cols: terminal.current?.cols || 80}),
  }), []);

  useEffect(() => {
    let disposed = false;
    let cleanup: (() => void) | undefined;
    Promise.all([import("@xterm/xterm"), import("@xterm/addon-fit")]).then(([{Terminal}, {FitAddon}]) => {
      if (disposed || !element.current) return;
      const term = new Terminal({cursorBlink: true, fontSize: 14, fontFamily: "Consolas, monospace",
        scrollback: 3000, disableStdin: !callbacks.current.enabled,
        theme: {background: "#020617", foreground: "#e2e8f0"}});
      const fit = new FitAddon();
      term.loadAddon(fit); term.open(element.current); terminal.current = term;
      const resize = () => {if (!disposed && element.current?.clientWidth) fit.fit();};
      const data = term.onData(value => {if (callbacks.current.enabled) callbacks.current.onInput(value);});
      const sized = term.onResize(({rows, cols}) => callbacks.current.onResize(rows, cols));
      const observer = new ResizeObserver(resize); observer.observe(element.current); resize();
      // Shift+Escape is an explicit keyboard route out of the terminal; Tab belongs to the shell.
      term.attachCustomKeyEventHandler(event => {
        if (event.key === "Escape" && event.shiftKey && event.type === "keydown") {
          element.current?.focus(); return false;
        }
        return true;
      });
      cleanup = () => {observer.disconnect(); data.dispose(); sized.dispose(); terminal.current = null; term.dispose();};
      callbacks.current.onReady();
    }).catch(error => {if (!disposed) callbacks.current.onError(`Terminal could not load: ${String(error)}`);});
    return () => {disposed = true; cleanup?.();};
  }, []);

  useLayoutEffect(() => {
    if (terminal.current) {
      terminal.current.options.disableStdin = !props.enabled;
      if (props.enabled) terminal.current.focus();
    }
  }, [props.enabled]);

  return <div ref={element} tabIndex={-1} onPointerUp={() => {
    if (callbacks.current.enabled && terminal.current) {
      terminal.current.options.disableStdin = false;
      terminal.current.focus();
    }
  }} aria-label="Interactive container terminal" className="h-96 min-w-0 overflow-hidden rounded bg-slate-950 p-2" />;
});
