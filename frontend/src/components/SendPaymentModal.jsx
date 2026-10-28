import { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  CreditCard,
  Lock,
  Printer,
  RefreshCw,
  Send,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Sparkles,
  UserCheck,
  UserX,
  X,
} from "lucide-react";
import { api } from "../api.js";

const PRESET_AMOUNTS = [100, 500, 1000, 2000, 5000];

export default function SendPaymentModal({ isOpen, onClose, balancePaise = 0, onPaymentSuccess }) {
  // Steps: 1: Select Recipient, 2: Verify Recipient, 3: Amount & Review, 4: Processing, 5: Receipt
  const [step, setStep] = useState(1);

  // Recipient input state
  const [recipientInput, setRecipientInput] = useState("");
  const [recipientType, setRecipientType] = useState("upi_id"); // "upi_id" | "mobile" | "handle"
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);

  // Payment details state
  const [amount, setAmount] = useState("5000"); // default ₹5000 for testing as requested
  const [note, setNote] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("sandbox_upi");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Final receipt data
  const [receipt, setReceipt] = useState(null);
  const [copiedRef, setCopiedRef] = useState(false);

  if (!isOpen) return null;

  const amountPaise = amount && !isNaN(amount) ? Math.round(parseFloat(amount) * 100) : 0;
  const platformFeePaise = 0; // ₹0 platform fee
  const totalPayablePaise = amountPaise + platformFeePaise;

  // Auto-detect identifier type
  const handleInputChange = (val) => {
    setRecipientInput(val);
    setError("");
    const cleaned = val.trim();
    if (/^[6-9]\d{9}$/.test(cleaned) || cleaned.startsWith("+91") || (cleaned.length === 10 && /^\d+$/.test(cleaned))) {
      setRecipientType("mobile");
    } else if (cleaned.includes("@")) {
      setRecipientType("upi_id");
    } else {
      setRecipientType("handle");
    }
  };

  // Step A -> Step B: Validate Recipient via Server
  const handleValidateRecipient = async (e) => {
    e.preventDefault();
    setError("");
    const trimmed = recipientInput.trim();
    if (!trimmed) {
      setError("Please enter a valid UPI ID (e.g. name@bank) or 10-digit mobile number.");
      return;
    }

    setValidating(true);
    try {
      const result = await api.validateRecipient({
        identifier: trimmed,
        identifier_type: recipientType,
      });

      if (!result.valid) {
        setError(result.message || "Invalid recipient format. Please check the details.");
        return;
      }

      setValidationResult(result);
      setStep(2);
    } catch (err) {
      setError(err.message || "Could not validate recipient. Verify connection.");
    } finally {
      setValidating(false);
    }
  };

  // Step B -> Step C: Proceed to Amount & Review
  const handleProceedToAmount = () => {
    setError("");
    setStep(3);
  };

  // Step C -> Step D & E: Execute Payment
  const handleExecutePayment = async () => {
    if (amountPaise <= 0) {
      setError("Please enter an amount greater than ₹0.");
      return;
    }

    if (amountPaise > 10000000) {
      setError("Amount exceeds sandbox maximum limit of ₹100,000.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    setStep(4);

    try {
      const idemKey = `pay-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      // 1. Create payment order on server
      const order = await api.createPaymentOrder({
        amount_paise: amountPaise,
        order_type: "payment",
        notes: note || `Payment to ${validationResult?.display_name || validationResult?.normalized_identifier}`,
        recipient_identifier: validationResult?.normalized_identifier,
        recipient_type: validationResult?.identifier_type,
        idempotency_key: idemKey,
      });

      // 2. Server-side signature verification & atomic settlement
      const verified = await api.verifyPayment({
        order_reference: order.order_reference,
        payment_id: `pay_${order.order_reference}`,
        signature: order.sandbox_signature,
      });

      // 3. Populate final verified receipt
      setReceipt({
        reference: verified.order_reference,
        amount_paise: verified.amount_paise,
        recipient_name: validationResult?.display_name || "Verified Recipient",
        recipient_identifier: validationResult?.normalized_identifier,
        recipient_type: validationResult?.identifier_type,
        note: note || "UPI P2P Payment",
        timestamp: new Date().toLocaleString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        status: "SUCCESSFUL",
        provider: "SecurePay NPCI Sandbox",
        receipt_number: `RCPT-${verified.order_reference.replace("ORD_", "")}`,
        sandbox: true,
      });

      setStep(5);
      if (onPaymentSuccess) onPaymentSuccess();
    } catch (err) {
      setError(err.message || "Payment processing failed. Transaction was not settled.");
      setStep(3); // return to review with error
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyRef = () => {
    if (receipt?.reference) {
      navigator.clipboard.writeText(receipt.reference);
      setCopiedRef(true);
      setTimeout(() => setCopiedRef(false), 2000);
    }
  };

  const handleReset = () => {
    setStep(1);
    setRecipientInput("");
    setValidationResult(null);
    setAmount("5000");
    setNote("");
    setError("");
    setReceipt(null);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={handleReset}>
      <div className="modal-card send-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header with Step Progress */}
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <Send size={18} />
            </div>
            <div>
              <h3 className="modal-title">Guided Payment Flow</h3>
              <p className="modal-subtitle">
                {step === 1 && "Step 1 of 4: Select Recipient"}
                {step === 2 && "Step 2 of 4: Review Verified Recipient"}
                {step === 3 && "Step 3 of 4: Configure Amount & Review"}
                {step === 4 && "Step 4 of 4: Processing Payment"}
                {step === 5 && "Payment Confirmed & Settled"}
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={handleReset} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {/* Step Progress Indicators */}
        <div className="payment-steps-bar">
          <div className={`step-dot ${step >= 1 ? "active" : ""}`}>1</div>
          <div className={`step-line ${step >= 2 ? "active" : ""}`} />
          <div className={`step-dot ${step >= 2 ? "active" : ""}`}>2</div>
          <div className={`step-line ${step >= 3 ? "active" : ""}`} />
          <div className={`step-dot ${step >= 3 ? "active" : ""}`}>3</div>
          <div className={`step-line ${step >= 5 ? "active" : ""}`} />
          <div className={`step-dot ${step >= 5 ? "active" : ""}`}>4</div>
        </div>

        {error && (
          <div className="alert-banner alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: Select Recipient */}
        {step === 1 && (
          <form onSubmit={handleValidateRecipient} className="modal-body-form animate-fade-in">
            <div className="form-group">
              <label className="input-label">Enter UPI ID or Indian Mobile Number</label>
              <div className="input-with-icon">
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. rahul@okaxis or 9876543210 or user.name"
                  value={recipientInput}
                  onChange={(e) => handleInputChange(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <small className="field-hint">
                Supported formats: standard UPI VPA (user@bank), 10-digit mobile number, or @securepay handle.
              </small>
            </div>

            <div className="identifier-type-pills mb-3">
              <button
                type="button"
                className={`type-pill ${recipientType === "upi_id" ? "active" : ""}`}
                onClick={() => setRecipientType("upi_id")}
              >
                UPI ID (VPA)
              </button>
              <button
                type="button"
                className={`type-pill ${recipientType === "mobile" ? "active" : ""}`}
                onClick={() => setRecipientType("mobile")}
              >
                Mobile Number
              </button>
              <button
                type="button"
                className={`type-pill ${recipientType === "handle" ? "active" : ""}`}
                onClick={() => setRecipientType("handle")}
              >
                Platform Handle
              </button>
            </div>

            <div className="sandbox-notice-pill mb-3">
              <ShieldCheck size={14} className="text-teal" />
              <span>Recipient verification runs on live/sandbox validation APIs without exposing private banking data.</span>
            </div>

            <div className="modal-actions-row">
              <button type="button" className="secondary-action-btn" onClick={handleReset}>
                Cancel
              </button>
              <button type="submit" className="primary-action-btn flex-1" disabled={validating}>
                {validating ? (
                  <>
                    <RefreshCw size={15} className="spin-icon" />
                    <span>Verifying Recipient...</span>
                  </>
                ) : (
                  <>
                    <span>Continue</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: Verify Recipient */}
        {step === 2 && validationResult && (
          <div className="modal-body-form animate-fade-in">
            <div className={`recipient-review-card ${validationResult.verified ? "verified" : "unverified"}`}>
              <div className="recipient-icon-wrap">
                {validationResult.verified ? (
                  <UserCheck size={32} className="text-teal" />
                ) : (
                  <ShieldAlert size={32} className="text-amber" />
                )}
              </div>

              <div className="recipient-review-info">
                <span className="recipient-type-tag">
                  {validationResult.identifier_type.toUpperCase()} RESOLUTION
                </span>
                <h3 className="recipient-display-title">
                  {validationResult.display_name || validationResult.normalized_identifier}
                </h3>
                <code className="recipient-identifier-text font-mono">
                  {validationResult.normalized_identifier}
                </code>

                <div className="verification-status-row mt-2">
                  {validationResult.verified ? (
                    <span className="verified-badge-pill">
                      <CheckCircle2 size={13} />
                      <span>Verified Recipient ({validationResult.verification_source.toUpperCase()})</span>
                    </span>
                  ) : (
                    <span className="unverified-badge-pill">
                      <ShieldAlert size={13} />
                      <span>{validationResult.message}</span>
                    </span>
                  )}
                </div>
              </div>
            </div>

            <p className="privacy-assurance-text text-muted text-sm mt-3 mb-3">
              Privacy Notice: As per NPCI guidelines, private account numbers and sensitive banking credentials are never exposed prior to settlement.
            </p>

            <div className="modal-actions-row">
              <button type="button" className="secondary-action-btn" onClick={() => setStep(1)}>
                Change Recipient
              </button>
              <button type="button" className="primary-action-btn flex-1" onClick={handleProceedToAmount}>
                <span>Proceed with this Recipient</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: Configure Amount & Review */}
        {step === 3 && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleExecutePayment();
            }}
            className="modal-body-form animate-fade-in"
          >
            {/* Amount input */}
            <div className="form-group">
              <label className="input-label">Payment Amount (INR)</label>
              <div className="currency-input-wrap large-input">
                <span className="currency-symbol">₹</span>
                <input
                  type="number"
                  min="1"
                  max="100000"
                  step="any"
                  placeholder="0.00"
                  className="amount-input"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              {/* Preset chips including ₹5,000 for test */}
              <div className="preset-chips-row">
                {PRESET_AMOUNTS.map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    className={`preset-chip ${parseFloat(amount) === amt ? "active" : ""}`}
                    onClick={() => setAmount(String(amt))}
                  >
                    ₹{amt.toLocaleString("en-IN")}
                  </button>
                ))}
              </div>
            </div>

            {/* Note / Purpose */}
            <div className="form-group">
              <label className="input-label">Note / Purpose (Optional)</label>
              <input
                type="text"
                className="form-input"
                placeholder="What is this payment for? (e.g. Dinner, Rent)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={80}
              />
            </div>

            {/* Review Summary Breakdown */}
            <div className="review-breakdown-box">
              <div className="breakdown-row">
                <span className="text-muted">Recipient</span>
                <strong>{validationResult?.display_name || validationResult?.normalized_identifier}</strong>
              </div>
              <div className="breakdown-row">
                <span className="text-muted">Identifier</span>
                <span className="font-mono text-muted">{validationResult?.normalized_identifier}</span>
              </div>
              <div className="breakdown-row">
                <span className="text-muted">Transfer Amount</span>
                <span>₹{(amountPaise / 100).toFixed(2)}</span>
              </div>
              <div className="breakdown-row">
                <span className="text-muted">Platform / Gateway Fee</span>
                <span className="text-teal font-semibold">₹0.00 (Zero MDR)</span>
              </div>
              <div className="breakdown-row total-row">
                <span>Total Payable</span>
                <strong className="text-teal">₹{(totalPayablePaise / 100).toFixed(2)}</strong>
              </div>
            </div>

            {/* Clear Sandbox Environment Badge */}
            <div className="sandbox-environment-banner mb-3">
              <ShieldCheck size={16} className="text-teal" />
              <div>
                <strong>SANDBOX — SIMULATED PAYMENT</strong>
                <p>NPCI Sandbox active. No real funds will be deducted from your bank account.</p>
              </div>
            </div>

            <div className="modal-actions-row">
              <button type="button" className="secondary-action-btn" onClick={() => setStep(2)}>
                Back
              </button>
              <button type="submit" className="primary-action-btn flex-1" disabled={isSubmitting}>
                <span>Authorize & Pay ₹{(totalPayablePaise / 100).toFixed(2)}</span>
                <Check size={16} />
              </button>
            </div>
          </form>
        )}

        {/* STEP 4: Processing State */}
        {step === 4 && (
          <div className="modal-body-processing text-center animate-fade-in py-5">
            <div className="processing-spinner-wrap mb-4">
              <RefreshCw size={44} className="spin-icon text-teal mx-auto" />
            </div>
            <h3>Authorizing Sandbox Payment...</h3>
            <p className="text-muted text-sm mt-2">
              Validating HMAC cryptographic signature and posting double-entry ledger settlement...
            </p>
          </div>
        )}

        {/* STEP 5: Payment Receipt */}
        {step === 5 && receipt && (
          <div className="modal-body-receipt animate-fade-in">
            <div className="receipt-status-banner success">
              <CheckCircle2 size={36} className="text-teal mx-auto mb-2" />
              <h2 className="receipt-headline">Payment Successful</h2>
              <div className="sandbox-watermark-pill">
                <span>SANDBOX — SIMULATED PAYMENT</span>
              </div>
            </div>

            <div className="receipt-amount-display text-center my-3">
              <span className="receipt-currency">₹</span>
              <span className="receipt-big-number">{(receipt.amount_paise / 100).toFixed(2)}</span>
            </div>

            {/* Receipt Details Table */}
            <div className="receipt-ticket-card">
              <div className="ticket-line">
                <span className="t-label">Transaction Reference:</span>
                <div className="d-flex align-center">
                  <code className="t-val font-mono">{receipt.reference}</code>
                  <button className="copy-icon-btn ml-1" onClick={handleCopyRef} title="Copy reference">
                    {copiedRef ? <Check size={14} className="text-teal" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              <div className="ticket-line">
                <span className="t-label">Receipt Number:</span>
                <span className="t-val font-mono">{receipt.receipt_number}</span>
              </div>

              <div className="ticket-line">
                <span className="t-label">Paid To:</span>
                <strong className="t-val text-teal">{receipt.recipient_name}</strong>
              </div>

              <div className="ticket-line">
                <span className="t-label">Recipient UPI / Mobile:</span>
                <span className="t-val font-mono">{receipt.recipient_identifier}</span>
              </div>

              <div className="ticket-line">
                <span className="t-label">Date & Time:</span>
                <span className="t-val">{receipt.timestamp}</span>
              </div>

              <div className="ticket-line">
                <span className="t-label">Payment Method:</span>
                <span className="t-val">UPI Interoperable Gateway</span>
              </div>

              <div className="ticket-line">
                <span className="t-label">Settlement Mode:</span>
                <span className="t-val">Double-Entry Ledger (Atomic)</span>
              </div>

              <div className="ticket-line">
                <span className="t-label">Verified Status:</span>
                <span className="status-badge-pill green">COMPLETED</span>
              </div>
            </div>

            <div className="modal-actions-row mt-4">
              <button
                type="button"
                className="secondary-action-btn"
                onClick={() => window.print()}
              >
                <Printer size={15} />
                <span>Print Receipt</span>
              </button>
              <button type="button" className="primary-action-btn flex-1" onClick={handleReset}>
                Done & View Ledger
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
