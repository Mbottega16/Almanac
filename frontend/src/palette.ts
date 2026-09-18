// Card headers are tinted with the colours of the linked site's own favicon,
// so a resource reads as "that site" before you read its title.
//
// The colours are precomputed offline by backend/scripts/build_palettes.py.
// They can't be read in the browser: Google's favicon service sends no CORS
// header, so a canvas that samples those pixels is tainted and throws.
import palettes from "./palettes.json";

const PALETTES = palettes as Record<string, string[]>;

export function hostOf(link: string): string {
  try {
    const { hostname } = new URL(link);
    const host = hostname.toLowerCase();
    return host.startsWith("www.") ? host.slice(4) : host;
  } catch {
    return "";
  }
}

// Domains with no usable icon still deserve to look distinct from each other,
// so derive a stable hue from the name rather than falling back to flat grey.
function fallbackColours(host: string): string[] {
  let hash = 0;
  for (let i = 0; i < host.length; i += 1) {
    hash = (hash * 31 + host.charCodeAt(i)) % 360;
  }
  return [`hsl(${hash} 55% 52%)`, `hsl(${(hash + 38) % 360} 48% 62%)`];
}

function withAlpha(colour: string, alpha: number): string {
  if (colour.startsWith("#")) {
    const hex = Math.round(alpha * 255).toString(16).padStart(2, "0");
    return `${colour}${hex}`;
  }
  // hsl(...) from the fallback — wrap it so the alpha applies the same way.
  return colour.replace(/^hsl\((.*)\)$/, (_m, body) => `hsla(${body} / ${alpha})`);
}

export interface CardTint {
  /** Vivid full-strength gradient — used for the thin rule at the card's top. */
  accent: string;
  /** The same colours at low alpha, so text over them stays readable in both
   *  light and dark mode without having to recompute a contrast colour. */
  wash: string;
}

export function tintFor(link: string): CardTint {
  const host = hostOf(link);
  const colours = PALETTES[host]?.length ? PALETTES[host] : fallbackColours(host);
  const stops = colours.length >= 2 ? colours : [colours[0], colours[0]];
  return {
    accent: `linear-gradient(90deg, ${stops.join(", ")})`,
    wash: `linear-gradient(135deg, ${stops.map((c) => withAlpha(c, 0.26)).join(", ")})`,
  };
}
