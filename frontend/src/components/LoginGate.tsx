import { useState } from "react";

import { login } from "../api/client";

/**
 * Shown only when the backend reports the auth gate is enabled and the
 * current session isn't authenticated. Dormant deployments never render this.
 */
export default function LoginGate({ onAuthed }: { onAuthed: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await login(password);
      if (res.ok) onAuthed();
      else setError(res.detail ?? "Wrong password");
    } catch {
      setError("Wrong password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-gate">
      <h1>Almanac</h1>
      <form onSubmit={submit}>
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={busy || !password}>
          {busy ? "…" : "Enter"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </div>
  );
}
