import { useEffect, useState } from "react";
import {
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileText,
  Printer,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
} from "lucide-react";
import { api } from "../api.js";

export default function TransactionReceiptModal({ isOpen, onClose, transaction }) {
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (isOpen && transaction?.reference) {
      setLoadingHistory(true);
      api
        .getOrderHistory(transaction.reference)
        .then((res) => setHistory(res || []))
        .catch(() => setHistory([]))
        .finally(() => setLoadingHistory(false));
    } else {
      setHistory([]);
    }
  }, [isOpen, transaction]);

  if (!isOpen || !transaction) return null;

  const isCredit = transaction.signed_amount_paise > 0;
  const formattedAmount = `₹${(Math.abs(transaction.amount_paise) / 100).toFixed(2)}`;

  const copyRef = () => {
    navigator.clipboard.writeText(transaction.reference);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card receipt-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <FileText size={18} />
            </div>
            <div>
              <h3 className="modal-title">Transaction Details & Audit Proof</h3>
              <p className="modal-subtitle">Cryptographically verified double-entry ledger entry</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="receipt-paper">
          {/* Status Header */}
          <div className="receipt-top-status">
            <div className={`receipt-badge-circle ${isCredit ? "bg-teal-subtle text-teal" : "bg-navy-subtle text-navy"}`}>
              <CheckCircle2 size={36} />
            </div>

            <div className="receipt-status-pill-wrap mt-2">
              <span className={`tx-status-pill ${isCredit ? "successful" : "posted"}`}>
                {transaction.status?.toUpperCase() || "SUCCESSFUL"}
              </span>
            </div>

            <h2 className={`receipt-big-amount ${isCredit ? "text-teal" : "text-navy"} my-2`}>
              {isCredit ? "+" : "-"}{formattedAmount}
            </h2>

            <span className="receipt-counterparty">{transaction.name}</span>
            {transaction.handle && (
              <small className="receipt-handle text-muted font-mono">@{transaction.handle}</small>
            )}
          </div>

          <div className="receipt-divider" />

          {/* Key Value Details */}
          <div className="receipt-grid-details">
            <div className="receipt-detail-item">
              <span className="detail-key">Transaction Ref:</span>
              <div className="detail-copy-wrap" onClick={copyRef}>
                <span className="detail-val font-mono">{transaction.reference}</span>
                <button className="copy-icon-btn" title="Copy reference">
                  {copied ? <Check size={12} className="text-teal" /> : <Copy size={12} />}
                </button>
              </div>
            </div>

            {transaction.id && (
              <div className="receipt-detail-item">
                <span className="detail-key">Ledger ID:</span>
                <span className="detail-val font-mono text-muted text-sm">{transaction.id}</span>
              </div>
            )}

            <div className="receipt-detail-item">
              <span className="detail-key">Direction:</span>
              <span className="detail-val font-semibold">{isCredit ? "Credit (Incoming)" : "Debit (Outgoing)"}</span>
            </div>

            <div className="receipt-detail-item">
              <span className="detail-key">Category:</span>
              <span className="detail-val">{transaction.category}</span>
            </div>

            <div className="receipt-detail-item">
              <span className="detail-key">Payment Method:</span>
              <span className="detail-val">{transaction.method || "SecurePay UPI"}</span>
            </div>

            <div className="receipt-detail-item">
              <span className="detail-key">Processing Fee:</span>
              <span className="detail-val text-teal font-semibold">₹0.00 (Zero MDR)</span>
            </div>

            <div className="receipt-detail-item">
              <span className="detail-key">Refund Status:</span>
              <span className="detail-val text-muted">Eligible via standard dispute workflow</span>
            </div>

            <div className="receipt-detail-item">
              <span className="detail-key">Date & Time:</span>
              <span className="detail-val">
                {transaction.created_at ? new Date(transaction.created_at).toLocaleString() : "Just now"}
              </span>
            </div>

            {transaction.note && (
              <div className="receipt-detail-item">
                <span className="detail-key">Note:</span>
                <span className="detail-val italic">"{transaction.note}"</span>
              </div>
            )}
          </div>

          {/* Status Transition History (Audit Log) */}
          {history.length > 0 && (
            <div className="receipt-history-section mt-3 pt-3 border-top">
              <span className="section-title-micro">STATUS AUDIT TRAIL</span>
              <div className="history-timeline mt-2">
                {history.map((h, i) => (
                  <div key={h.id || i} className="timeline-node">
                    <div className="timeline-dot" />
                    <div className="timeline-body">
                      <strong>{h.new_status.toUpperCase()}</strong>
                      <span className="text-muted text-sm"> • {new Date(h.created_at).toLocaleTimeString()}</span>
                      {h.reason && <p className="text-muted text-sm mt-1">{h.reason}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="receipt-watermark-row mt-3">
            <ShieldCheck size={14} className="text-teal" />
            <span>SANDBOX — SIMULATED PAYMENT • 256-bit Immutable Double-Entry Ledger</span>
          </div>
        </div>

        <div className="modal-actions-row">
          <button className="secondary-action-btn flex-1" onClick={handlePrint}>
            <Printer size={15} />
            <span>Print Receipt</span>
          </button>
          <button className="primary-action-btn flex-1" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
