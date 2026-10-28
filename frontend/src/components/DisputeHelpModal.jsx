import { AlertTriangle, Check, FileQuestion, HelpCircle, Lock, MessageSquare, PhoneCall, ShieldAlert, X } from "lucide-react";
import { useState } from "react";

export default function DisputeHelpModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState("faq"); // 'faq' | 'dispute' | 'fraud'
  const [disputeRef, setDisputeRef] = useState("");
  const [disputeReason, setDisputeReason] = useState("Transaction amount debited but not credited");
  const [disputeSubmitted, setDisputeSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmitDispute = (e) => {
    e.preventDefault();
    setDisputeSubmitted(true);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card help-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <HelpCircle size={20} />
            </div>
            <div>
              <h3 className="modal-title">Help & Dispute Resolution</h3>
              <p className="modal-subtitle">24/7 payment assistance and security protection</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="help-tab-bar">
          <button
            className={`help-tab ${activeTab === "faq" ? "active" : ""}`}
            onClick={() => setActiveTab("faq")}
          >
            <FileQuestion size={15} />
            <span>FAQs</span>
          </button>
          <button
            className={`help-tab ${activeTab === "dispute" ? "active" : ""}`}
            onClick={() => setActiveTab("dispute")}
          >
            <MessageSquare size={15} />
            <span>Raise Dispute</span>
          </button>
          <button
            className={`help-tab ${activeTab === "fraud" ? "active" : ""}`}
            onClick={() => setActiveTab("fraud")}
          >
            <ShieldAlert size={15} />
            <span>Report Fraud</span>
          </button>
        </div>

        <div className="modal-body-scroll">
          {activeTab === "faq" && (
            <div className="faq-list">
              <div className="faq-item">
                <strong className="faq-q">How does SecurePay ensure transaction privacy?</strong>
                <p className="faq-a">
                  We enforce zero-knowledge architecture. Sensitive credentials such as UPI PINs, ATM PINs, card CVVs, and raw bank account numbers are never collected, logged, or stored on our servers.
                </p>
              </div>
              <div className="faq-item">
                <strong className="faq-q">What is the difference between Sandbox and Live payments?</strong>
                <p className="faq-a">
                  In Sandbox mode, all transactions execute within our cryptographically verified double-entry test ledger with zero actual bank deduction. Live payments require authorized provider onboarding.
                </p>
              </div>
              <div className="faq-item">
                <strong className="faq-q">How quickly are refunds settled?</strong>
                <p className="faq-a">
                  UPI refunds are processed instantly. Bank-to-bank NEFT/IMPS reversals typically settle within 2 to 4 hours in accordance with RBI guidelines.
                </p>
              </div>
            </div>
          )}

          {activeTab === "dispute" && (
            <div className="dispute-pane">
              {disputeSubmitted ? (
                <div className="dispute-success-box">
                  <Check size={36} className="text-teal" />
                  <h4>Grievance Ticket Registered</h4>
                  <p>Ticket #DSP-{Math.floor(100000 + Math.random() * 900000)} has been opened.</p>
                  <small>Our automated reconciliation engine will review the ledger and update you within 24 hours.</small>
                  <button className="secondary-action-btn mt-4" onClick={() => setDisputeSubmitted(false)}>
                    File Another Dispute
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmitDispute} className="dispute-form">
                  <div className="form-group">
                    <label className="input-label">Transaction Reference Number</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. TX_8A9B2C or ORD_..."
                      value={disputeRef}
                      onChange={(e) => setDisputeRef(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="input-label">Issue Category</label>
                    <select
                      className="form-select"
                      value={disputeReason}
                      onChange={(e) => setDisputeReason(e.target.value)}
                    >
                      <option value="Transaction amount debited but not credited">
                        Amount debited but not credited to recipient
                      </option>
                      <option value="Duplicate payment charged">
                        Duplicate payment charged for single order
                      </option>
                      <option value="Incorrect recipient handle">
                        Sent money to incorrect handle
                      </option>
                      <option value="Merchant order not fulfilled">
                        Merchant order paid but not fulfilled
                      </option>
                    </select>
                  </div>

                  <button type="submit" className="primary-action-btn w-full">
                    Submit Dispute for Investigation
                  </button>
                </form>
              )}
            </div>
          )}

          {activeTab === "fraud" && (
            <div className="fraud-pane">
              <div className="fraud-warning-card">
                <AlertTriangle size={24} className="text-amber" />
                <div>
                  <strong>Suspect Fraud or Unauthorized Access?</strong>
                  <p>You can instantly lock all active browser sessions and rotate your password from Security Settings.</p>
                </div>
              </div>

              <div className="fraud-actions-list">
                <div className="fraud-contact-item">
                  <PhoneCall size={20} className="text-teal" />
                  <div>
                    <strong>24x7 Cyber Crime Helpline (India)</strong>
                    <span className="contact-val">Dial 1930 / https://cybercrime.gov.in</span>
                  </div>
                </div>
                <div className="fraud-contact-item">
                  <Lock size={20} className="text-teal" />
                  <div>
                    <strong>Emergency Account Freeze</strong>
                    <span className="contact-val">Go to Security Settings &gt; Revoke All Remote Sessions</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
