import { useState } from "react";
import { ArrowRight, LockKeyhole, ShieldCheck, Sparkles, Wallet } from "lucide-react";
import { apiRequest } from "../api.js";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [displayName, setDisplayName] = useState("");
  const [demoHandle, setDemoHandle] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    if (mode === "register" && !/^[A-Za-z0-9._-]{3,30}$/.test(demoHandle.trim())) {
      setError("Choose a Profile ID with 3–30 letters, numbers, periods, underscores, or hyphens. Do not use an email address.");
      return;
    }
    setBusy(true);
    try {
      const path = mode === "register" ? "/auth/register" : "/auth/login";
      const body = mode === "register"
        ? { display_name: displayName.trim(), demo_handle: demoHandle.trim(), password }
        : { demo_handle: demoHandle.trim(), password };
      const response = await apiRequest(path, { method: "POST", body });
      if (mode === "register") {
        setMode("login");
        setPassword("");
        setMessage("Account created. Sign in with your Profile ID and password.");
        return;
      }
      onAuthenticated(response.user);
    } catch (requestError) {
      setError(requestError.message || "Unable to sign in right now.");
    } finally {
      setBusy(false);
    }
  };

  const requestRecovery = async () => {
    setError("");
    setMessage("");
    try {
      const response = await apiRequest("/auth/recovery", { method: "POST", body: {} });
      setMessage(response.message);
    } catch (requestError) {
      setError(requestError.message || "Unable to request recovery.");
    }
  };

  return <main className="auth-page">
    <section className="auth-story">
      <a href="/" className="brand auth-brand">
        <span className="brand-icon"><Wallet size={20} strokeWidth={2.2} /></span>
        <span className="brand-name">secure<span>pay</span><small>PAYMENTS, SIMPLIFIED</small></span>
      </a>
      <div className="auth-story-content">
        <span className="auth-badge"><Sparkles size={14} /> SERVICES NOT CONNECTED</span>
        <h1>Your account,<br />all in one place.</h1>
        <p>Manage your SecurePay profile and account security in one place.</p>
        <div className="auth-promise"><ShieldCheck size={18} /><span><strong>SecurePay account</strong><small>Payment services are not connected.</small></span></div>
      </div>
      <span className="auth-story-footer">SecurePay · Payments</span>
      <div className="auth-decoration auth-decoration-one" /><div className="auth-decoration auth-decoration-two" />
    </section>
    <section className="auth-form-side">
      <div className="auth-form-wrap">
        <span className="auth-mobile-brand"><span className="brand-icon"><Wallet size={18} /></span> SecurePay <span>ACCOUNT</span></span>
        <span className="auth-small-label">SECUREPAY ACCOUNT</span>
        <h2>{mode === "register" ? "Create your profile" : "Welcome back"}</h2>
        <p className="auth-intro">{mode === "register" ? "Create your SecurePay account." : "Sign in to your SecurePay account."}</p>
        <div className="auth-mode-switch" role="tablist" aria-label="Authentication mode">
          <button role="tab" aria-selected={mode === "login"} className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setError(""); setMessage(""); }}>Sign in</button>
          <button role="tab" aria-selected={mode === "register"} className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setError(""); setMessage(""); }}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && <label className="field-label">Display name<input required minLength="1" maxLength="60" autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Your name" /></label>}
          <label className="field-label">Profile ID<input required minLength={mode === "register" ? "3" : "1"} maxLength="30" autoComplete="username" value={demoHandle} onChange={(event) => setDemoHandle(event.target.value)} placeholder="Your profile ID" /></label>
          {mode === "register" && <small className="auth-field-hint">3–30 letters, numbers, dots, underscores, or hyphens. No email address. Phone verification is not available.</small>}
          <label className="field-label">Password<input required minLength={mode === "register" ? "12" : "1"} maxLength="128" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === "register" ? "At least 12 characters" : "Your password"} /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          {message && <p className="auth-message" role="status">{message}</p>}
          <button className="button button-primary button-full auth-submit" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}{!busy && <ArrowRight size={16} />}</button>
        </form>
        {mode === "login" && <button className="auth-recovery" onClick={requestRecovery}>Forgot your password?</button>}
        <div className="auth-privacy"><LockKeyhole size={15} /><span>Never enter a banking password, UPI PIN, OTP, or card details. These services are not connected.</span></div>
        <p className="auth-disclaimer">No bank or payment provider is connected. <strong>Payments cannot be sent or received.</strong></p>
      </div>
    </section>
  </main>;
}
