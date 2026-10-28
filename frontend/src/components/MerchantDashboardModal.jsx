import { useEffect, useState } from "react";
import { AlertCircle, Building2, Check, CheckCircle2, Copy, QrCode, RefreshCw, ShieldCheck, Sparkles, Store, TrendingUp, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../api.js";

export default function MerchantDashboardModal({ isOpen, onClose }) {
  const [merchant, setMerchant] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  // Registration form state
  const [businessName, setBusinessName] = useState("");
  const [category, setCategory] = useState("Retail & Groceries");
  const [submitting, setSubmitting] = useState(false);

  const loadMerchant = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getMerchantProfile();
      setMerchant(data);
    } catch (err) {
      if (err.statusCode === 404) {
        setMerchant(null);
      } else {
        setError(err.message || "Failed to load merchant profile.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadMerchant();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleRegister = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const res = await api.registerMerchant({
        business_name: businessName,
        category: category,
      });
      setMerchant(res);
    } catch (err) {
      setError(err.message || "Failed to activate merchant account.");
    } finally {
      setSubmitting(false);
    }
  };

  const copyUpi = () => {
    if (merchant?.upi_handle) {
      navigator.clipboard.writeText(merchant.upi_handle);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const qrUrl = merchant?.upi_handle
    ? `upi://pay?pa=${merchant.upi_handle}&pn=${encodeURIComponent(merchant.business_name)}&cu=INR`
    : "";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card merchant-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge teal-badge">
              <Store size={20} />
            </div>
            <div>
              <h3 className="modal-title">Merchant Center</h3>
              <p className="modal-subtitle">Accept customer payments with 0% platform fee</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="alert-banner alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <div className="modal-body-scroll">
          {loading ? (
            <div className="skeleton-loading-wrap">
              <div className="skeleton-line" />
              <div className="skeleton-line" />
            </div>
          ) : merchant ? (
            <div className="merchant-active-view">
              <div className="merchant-hero-card">
                <div className="merchant-meta-top">
                  <span className="merchant-badge-active">
                    <CheckCircle2 size={13} />
                    <span>ACTIVE MERCHANT</span>
                  </span>
                  <span className="merchant-code-chip">{merchant.merchant_code}</span>
                </div>
                <h3 className="merchant-business-title">{merchant.business_name}</h3>
                <p className="merchant-cat-text">{merchant.category}</p>

                <div className="merchant-upi-box" onClick={copyUpi}>
                  <span className="upi-handle-label">Business UPI ID:</span>
                  <span className="upi-handle-val">{merchant.upi_handle}</span>
                  <button className="copy-btn-sm" title="Copy UPI ID">
                    {copied ? <Check size={14} className="text-teal" /> : <Copy size={14} />}
                  </button>
                </div>
              </div>

              <div className="storefront-qr-card">
                <div className="qr-head-row">
                  <QrCode size={18} className="text-teal" />
                  <h4>Storefront Payment QR</h4>
                </div>
                <p className="qr-sub-text">Display this QR code at your checkout counter</p>
                <div className="storefront-qr-box">
                  <QRCodeSVG
                    value={qrUrl}
                    size={190}
                    level="H"
                    includeMargin={true}
                    bgColor="#FFFFFF"
                    fgColor="#0A192F"
                  />
                </div>
              </div>

              <div className="merchant-features-row">
                <div className="m-feature-pill">
                  <Sparkles size={16} className="text-teal" />
                  <div>
                    <strong>0% Transaction Fee</strong>
                    <small>Zero MDR on all UPI payments</small>
                  </div>
                </div>
                <div className="m-feature-pill">
                  <TrendingUp size={16} className="text-teal" />
                  <div>
                    <strong>Instant Settlement</strong>
                    <small>Direct to primary bank account</small>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleRegister} className="merchant-onboarding-form">
              <div className="onboarding-banner">
                <Store size={36} className="text-teal" />
                <h4>Accept Payments for Your Business</h4>
                <p>Register as a verified SecurePay merchant in seconds and receive your branded UPI QR code.</p>
              </div>

              <div className="form-group">
                <label className="input-label">Business / Store Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Blue Tokai Roasters"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  required
                  minLength={2}
                  maxLength={120}
                />
              </div>

              <div className="form-group">
                <label className="input-label">Business Category</label>
                <select
                  className="form-select"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="Retail & Groceries">Retail & Groceries</option>
                  <option value="Food & Beverages">Food & Beverages</option>
                  <option value="Electronics & Tech">Electronics & Tech</option>
                  <option value="Health & Pharmacy">Health & Pharmacy</option>
                  <option value="Freelance & Consulting">Freelance & Consulting</option>
                  <option value="Other Business Services">Other Business Services</option>
                </select>
              </div>

              <div className="merchant-benefits-card">
                <div className="benefit-item">
                  <Check size={16} className="text-teal" />
                  <span>Branded UPI ID (`yourbusiness.merch@securepay`)</span>
                </div>
                <div className="benefit-item">
                  <Check size={16} className="text-teal" />
                  <span>Real-time webhook events and double-entry ledger</span>
                </div>
                <div className="benefit-item">
                  <Check size={16} className="text-teal" />
                  <span>Full sandbox payment testing and order APIs</span>
                </div>
              </div>

              <button type="submit" className="primary-action-btn w-full" disabled={submitting}>
                {submitting ? "Activating Merchant..." : "Activate Merchant Account"}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
