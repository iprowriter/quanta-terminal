"use client";

import { useState, useEffect, useRef } from "react";

/**
 * Animates a string by revealing it character-by-character.
 *
 * Usage:
 *   const displayed = useTypewriter(fullText, { speed: 8 });
 *
 * - While `fullText` is "" (loading), `displayed` is "".
 * - As soon as `fullText` is set, it streams character by character.
 * - If `fullText` changes mid-animation (e.g. regeneration), it resets.
 */
export function useTypewriter(
  text: string,
  options: {
    speed?: number;  // characters per tick
    delay?: number;  // ms between ticks (default 16 ≈ 60fps)
  } = {},
): string {
  const { speed = 3, delay = 16 } = options;

  const [displayed, setDisplayed] = useState("");
  const indexRef   = useRef(0);
  const textRef    = useRef(text);

  // Reset when the source text changes
  useEffect(() => {
    if (text !== textRef.current) {
      textRef.current = text;
      indexRef.current = 0;
      setDisplayed("");
    }
  }, [text]);

  useEffect(() => {
    if (!text) return;
    indexRef.current = 0;
    textRef.current  = text;
    setDisplayed("");

    const tick = setInterval(() => {
      const next = indexRef.current + speed;
      setDisplayed(textRef.current.slice(0, next));
      indexRef.current = next;

      if (next >= textRef.current.length) {
        clearInterval(tick);
      }
    }, delay);

    return () => clearInterval(tick);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  return displayed;
}
