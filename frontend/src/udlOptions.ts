import { UdlPrinciple } from "./api/client";

// A short menu of ways to widen a lesson, grouped by UDL principle. Each option is one
// concrete move a teacher can make; they follow the CAST UDL guidelines in plain words.
export interface UdlOption {
  key: string;
  label: string;
  hint: string;
}

export const UDL_OPTIONS: Record<UdlPrinciple, UdlOption[]> = {
  engagement: [
    { key: "choice", label: "Offer choice", hint: "Let students pick the topic, tool, or order of tasks." },
    { key: "relevance", label: "Connect to students' lives", hint: "Use examples from their world, culture, or interests." },
    { key: "calm", label: "Lower distractions and threat", hint: "Predictable routine, clear steps, low-stakes first try." },
    { key: "goals", label: "Set goals and give feedback", hint: "Show the goal up front. Give feedback while they work." },
    { key: "together", label: "Build in collaboration", hint: "Pairs or small groups with clear roles." },
    { key: "reflect", label: "Add self-reflection", hint: "A short check on what worked and what to try next." },
  ],
  representation: [
    { key: "audio", label: "Offer audio or read-aloud", hint: "Text-to-speech, a recording, or a teacher read-aloud." },
    { key: "visual", label: "Add visuals", hint: "Diagrams, photos, video, or a model to see." },
    { key: "vocab", label: "Support vocabulary", hint: "Glossary, word wall, or pictured key terms." },
    { key: "prior", label: "Activate background knowledge", hint: "A quick hook or review before the new idea." },
    { key: "patterns", label: "Highlight patterns", hint: "Color, bold, or sentence frames that show the key idea." },
    { key: "examples", label: "Give more than one example", hint: "Show the idea in two or three different forms." },
  ],
  action_expression: [
    { key: "show", label: "Allow more than one way to show learning", hint: "Write, draw, speak, build, or record." },
    { key: "tools", label: "Offer tools and assistive tech", hint: "Speech-to-text, calculators, manipulatives, graphic organizers." },
    { key: "plan", label: "Support planning", hint: "Checklist, template, or a short plan step before the work." },
    { key: "chunk", label: "Break work into steps", hint: "Short chunks with a check after each one." },
    { key: "scaffold", label: "Scaffold practice", hint: "Worked examples first, then less support." },
    { key: "pace", label: "Allow flexible pacing", hint: "Extra time, a stopping point, or an extension task." },
  ],
};
