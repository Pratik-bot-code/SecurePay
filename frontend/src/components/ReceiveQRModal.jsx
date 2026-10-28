import { useState } from "react";
import { Check, Copy, Download, QrCode, Share2, Sparkles, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

export default function ReceiveQRModal({ isOpen, onClose, user }) {
  const [copied, setCopied] = useState(false);
  const [customAmount, setCustomAmount] = useState("");

  if (!isOpen) return null;

  const handle = user?.demo_handle || user?.handle || "user";
  const upiId = `${handle}@securepay`;

  const amountPaise = customAmount && !isNaN(customAmount) ? Math.round(parseFloat(customAmount) * 100) : 0;
  const upiUrl = amountPaise > 0
    ? `upi://pay?pa=${upiId}&pn=${encodeURIComponent(user?.display_name || handle)}&am=${(amountPaise / 100).toFixed(2)}&cu=INR`
    : `upi://pay?pa=${upiId}&pn=${encodeURIComponent(user?.display_name || handle)}&cu=INR`;

  const copyUpiId = () => {
    navigator.clipboard.writeText(upiId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card qr-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <QrCode size={20} />
            </div>
            <div>
              <h3 className="modal-title">Receive Payment</h3>
              <p className="modal-subtitle">Scan to pay via any UPI app</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="qr-container">
          <div className="qr-badge-banner">
            <Sparkles size={14} />
            <span>Instant UPI & Sandbox Settlement</span>
          </div>

          <div className="qr-code-frame">
            <QRCodeSVG
              value={upiUrl}
              size={210}
              level="H"
              includeMargin={true}
              bgColor="#FFFFFF"
              fgColor="#0F172A"
            />
          </div>

          <div className="qr-user-info">
            <h4 className="qr-user-name">{user?.display_name || "SecurePay User"}</h4>
            <div className="upi-id-pill" onClick={copyUpiId}>
              <span className="upi-id-text">{upiId}</span>
              <button className="copy-btn" title="Copy UPI ID">
                {copied ? <Check size={14} className="text-teal" /> : <Copy size={14} />}
              </button>
            </div>
            {copied && <span className="copied-toast">UPI ID copied to clipboard!</span>}
          </div>

          <div className="qr-amount-section">
            <label htmlFor="custom-amount-input" className="input-label">
              Set specific amount (optional)
            </label>
            <div className="currency-input-wrap">
              <span className="currency-symbol">₹</span>
              <input
                id="custom-amount-input"
                type="number"
                min="1"
                step="1"
                placeholder="0.00"
                value={customAmount}
                onChange={(e) => setCustomAmount(e.target.value)}
                className="amount-input"
              />
            </div>
            {amountPaise > 0 && (
              <p className="amount-caption">
                Requesting <strong>₹{(amountPaise / 100).toFixed(2)}</strong>
              </p>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="secondary-action-btn" onClick={copyUpiId}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            <span>{copied ? "Copied" : "Copy UPI Link"}</span>
          </button>
          <button className="primary-action-btn" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
