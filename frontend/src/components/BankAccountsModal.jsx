import { useEffect, useState } from "react";
import {
  AlertCircle,
  Building2,
  Check,
  CheckCircle2,
  ChevronRight,
  Filter,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { api } from "../api.js";

const CATEGORY_LABELS = {
  all: "All Institutions",
  public_sector: "Public Sector",
  private_sector: "Private Sector",
  small_finance: "Small Finance",
  payments_bank: "Payments Bank",
  regional_rural: "Regional Rural",
};

export default function BankAccountsModal({ isOpen, onClose, onAccountUpdated }) {
  const [banks, setBanks] = useState([]);
  const [directory, setDirectory] = useState([]);
  const [directoryLoading, setDirectoryLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState("list"); // "list" | "directory" | "form"

  // Directory filter state
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [supportedOnly, setSupportedOnly] = useState(false);

  // Form state
  const [selectedInstitution, setSelectedInstitution] = useState(null);
  const [bankName, setBankName] = useState("");
  const [holderName, setHolderName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [confirmAccountNumber, setConfirmAccountNumber] = useState("");
  const [ifscCode, setIfscCode] = useState("");
  const [accountType, setAccountType] = useState("savings");
  const [submitting, setSubmitting] = useState(false);

  const loadBanks = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getLinkedBanks();
      setBanks(data || []);
    } catch (err) {
      setError(err.message || "Failed to load bank accounts.");
    } finally {
      setLoading(false);
    }
  };

  const loadDirectory = async () => {
    setDirectoryLoading(true);
    try {
      const data = await api.getBankDirectory({
        search,
        category,
        supported_only: supportedOnly,
      });
      setDirectory(data || []);
    } catch {
      setDirectory([]);
    } finally {
      setDirectoryLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadBanks();
      setView("list");
      setError("");
    }
  }, [isOpen]);

  useEffect(() => {
    if (view === "directory") {
      loadDirectory();
    }
  }, [view, search, category, supportedOnly]);

  if (!isOpen) return null;

  const handleSelectBank = (inst) => {
    setSelectedInstitution(inst);
    setBankName(inst.name);
    setIfscCode(`${inst.ifsc_prefix}0000001`);
    setView("form");
  };

  const handleAddBank = async (e) => {
    e.preventDefault();
    setError("");

    if (accountNumber !== confirmAccountNumber) {
      setError("Account numbers do not match. Please verify.");
      return;
    }

    if (!/^[0-9]{9,18}$/.test(accountNumber.trim())) {
      setError("Account number must be between 9 and 18 digits.");
      return;
    }

    if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(ifscCode.trim().toUpperCase())) {
      setError("Invalid IFSC code format (must be 11 characters, 5th character '0', e.g., SBIN0001234).");
      return;
    }

    setSubmitting(true);
    try {
      await api.linkBank({
        bank_name: bankName,
        account_holder_name: holderName,
        account_number: accountNumber,
        ifsc_code: ifscCode.trim().toUpperCase(),
        account_type: accountType,
      });
      setView("list");
      setAccountNumber("");
      setConfirmAccountNumber("");
      setHolderName("");
      setSelectedInstitution(null);
      await loadBanks();
      if (onAccountUpdated) onAccountUpdated();
    } catch (err) {
      setError(err.message || "Failed to link bank account. Verify details.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSetPrimary = async (bankId) => {
    try {
      await api.setPrimaryBank(bankId);
      await loadBanks();
      if (onAccountUpdated) onAccountUpdated();
    } catch (err) {
      setError(err.message || "Failed to set primary bank.");
    }
  };

  const handleUnlink = async (bankId) => {
    if (!window.confirm("Are you sure you want to unlink this bank account?")) return;
    try {
      await api.unlinkBank(bankId);
      await loadBanks();
      if (onAccountUpdated) onAccountUpdated();
    } catch (err) {
      setError(err.message || "Failed to unlink account.");
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card bank-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <Building2 size={20} />
            </div>
            <div>
              <h3 className="modal-title">Indian Bank Directory & Accounts</h3>
              <p className="modal-subtitle">
                {view === "list" && "Manage your linked settlement accounts"}
                {view === "directory" && "Select from verified Indian financial institutions"}
                {view === "form" && "Complete account linking details"}
              </p>
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
          {/* VIEW 1: Linked Accounts List */}
          {view === "list" && (
            <div className="bank-list-section">
              <div className="section-head-bar">
                <span className="section-title-small">LINKED ACCOUNTS ({banks.length})</span>
                <button className="add-bank-btn" onClick={() => setView("directory")}>
                  <Plus size={15} />
                  <span>Link New Bank</span>
                </button>
              </div>

              {loading ? (
                <div className="skeleton-loading-wrap">
                  <div className="skeleton-line" />
                  <div className="skeleton-line" />
                </div>
              ) : banks.length === 0 ? (
                <div className="empty-bank-state">
                  <Building2 size={40} className="empty-icon text-muted" />
                  <h4>No linked bank accounts yet</h4>
                  <p>Link your savings or current account from any verified Indian bank to enable payouts.</p>
                  <button className="primary-action-btn mt-2" onClick={() => setView("directory")}>
                    <Plus size={16} />
                    <span>Browse Bank Directory</span>
                  </button>
                </div>
              ) : (
                <div className="bank-cards-grid">
                  {banks.map((bank) => (
                    <div key={bank.id} className={`bank-item-card ${bank.is_primary ? "primary-bank" : ""}`}>
                      <div className="bank-item-icon">
                        <Building2 size={22} />
                      </div>
                      <div className="bank-item-details">
                        <div className="bank-name-row">
                          <strong className="bank-name">{bank.bank_name}</strong>
                          {bank.is_primary ? (
                            <span className="primary-tag">Primary Account</span>
                          ) : (
                            <button
                              className="set-primary-link"
                              onClick={() => handleSetPrimary(bank.id)}
                            >
                              Set as Primary
                            </button>
                          )}
                        </div>
                        <div className="bank-meta-row">
                          <span>{bank.account_holder_name}</span>
                          <span className="dot-sep">•</span>
                          <span className="account-masked">{bank.masked_account_number}</span>
                          <span className="dot-sep">•</span>
                          <span>{bank.ifsc_code}</span>
                        </div>
                        <div className="verification-badge">
                          <ShieldCheck size={14} className="text-teal" />
                          <span>NPCI Verified • {bank.account_type.toUpperCase()}</span>
                        </div>
                      </div>
                      <button
                        className="unlink-btn"
                        onClick={() => handleUnlink(bank.id)}
                        title="Unlink Account"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* VIEW 2: Indian Bank Directory Selector */}
          {view === "directory" && (
            <div className="bank-directory-section animate-fade-in">
              <div className="d-flex justify-between align-center mb-3">
                <button className="secondary-action-btn" onClick={() => setView("list")}>
                  ← Back to My Accounts
                </button>
                <div className="directory-stats text-muted text-sm">
                  {directory.length} Institutions Found
                </div>
              </div>

              {/* Search & Category Filter */}
              <div className="search-input-wrap mb-3">
                <Search size={16} className="search-icon text-muted" />
                <input
                  type="text"
                  className="filter-search-input"
                  placeholder="Search by bank name or IFSC prefix (e.g. SBI, HDFC, ICIC)..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  autoFocus
                />
              </div>

              {/* Category Pills */}
              <div className="bank-category-chips mb-3">
                {Object.entries(CATEGORY_LABELS).map(([catKey, catLabel]) => (
                  <button
                    key={catKey}
                    type="button"
                    className={`category-chip ${category === catKey ? "active" : ""}`}
                    onClick={() => setCategory(catKey)}
                  >
                    {catLabel}
                  </button>
                ))}
              </div>

              {/* Supported Filter Toggle */}
              <label className="supported-toggle-label mb-3">
                <input
                  type="checkbox"
                  checked={supportedOnly}
                  onChange={(e) => setSupportedOnly(e.target.checked)}
                />
                <span>Show only institutions with instant sandbox linking supported</span>
              </label>

              {directoryLoading ? (
                <div className="skeleton-loading-wrap">
                  <div className="skeleton-line" />
                  <div className="skeleton-line" />
                  <div className="skeleton-line" />
                </div>
              ) : directory.length === 0 ? (
                <div className="empty-bank-state">
                  <Building2 size={36} className="text-muted" />
                  <h4>No institutions match your search</h4>
                  <p>Try searching for a different bank name or reset category filters.</p>
                </div>
              ) : (
                <div className="directory-banks-grid">
                  {directory.map((inst) => (
                    <div
                      key={inst.code}
                      className={`directory-bank-card ${inst.supported_for_linking ? "supported" : "unsupported"}`}
                      onClick={() => {
                        if (inst.supported_for_linking) {
                          handleSelectBank(inst);
                        } else {
                          setError(`${inst.name} is listed in the directory, but instant linking is pending provider onboarding. Please choose a supported bank (e.g. SBI, HDFC, ICICI, Axis, Kotak).`);
                        }
                      }}
                    >
                      <div className="inst-header">
                        <div className="inst-icon-circle">
                          <Building2 size={18} />
                        </div>
                        <div className="inst-names">
                          <strong className="inst-title">{inst.name}</strong>
                          <span className="inst-short">{inst.short_name} • {inst.ifsc_prefix}</span>
                        </div>
                      </div>

                      <p className="inst-tagline text-muted text-sm">{inst.tagline}</p>

                      <div className="inst-footer">
                        {inst.supported_for_linking ? (
                          <span className="linking-status-badge supported">
                            <CheckCircle2 size={13} />
                            <span>Instant Linking</span>
                          </span>
                        ) : (
                          <span className="linking-status-badge pending">
                            <ShieldAlert size={13} />
                            <span>Penny Drop Required</span>
                          </span>
                        )}
                        <ChevronRight size={16} className="text-muted" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* VIEW 3: Account Linking Form */}
          {view === "form" && (
            <form onSubmit={handleAddBank} className="modal-body-form animate-fade-in">
              <div className="d-flex justify-between align-center mb-3">
                <button
                  type="button"
                  className="secondary-action-btn"
                  onClick={() => setView("directory")}
                >
                  ← Choose Another Bank
                </button>
                {selectedInstitution && (
                  <span className="linking-tag text-teal font-semibold">
                    {selectedInstitution.name}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label className="input-label">Bank Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="input-label">Account Holder Name (as per bank records)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Rahul Sharma"
                  value={holderName}
                  onChange={(e) => setHolderName(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="input-label">Account Number</label>
                <input
                  type="password"
                  className="form-input font-mono"
                  placeholder="Enter 9–18 digit account number"
                  value={accountNumber}
                  onChange={(e) => setAccountNumber(e.target.value)}
                  maxLength={18}
                  required
                />
                <small className="field-hint">Never stored in plain text. Only last 4 digits are saved.</small>
              </div>

              <div className="form-group">
                <label className="input-label">Confirm Account Number</label>
                <input
                  type="text"
                  className="form-input font-mono"
                  placeholder="Re-enter account number"
                  value={confirmAccountNumber}
                  onChange={(e) => setConfirmAccountNumber(e.target.value)}
                  maxLength={18}
                  required
                />
              </div>

              <div className="form-group">
                <label className="input-label">Branch IFSC Code</label>
                <input
                  type="text"
                  className="form-input font-mono"
                  placeholder="e.g. SBIN0001234"
                  value={ifscCode}
                  onChange={(e) => setIfscCode(e.target.value.toUpperCase())}
                  maxLength={11}
                  required
                />
              </div>

              <div className="form-group">
                <label className="input-label">Account Type</label>
                <div className="radio-pill-group">
                  <button
                    type="button"
                    className={`radio-pill ${accountType === "savings" ? "active" : ""}`}
                    onClick={() => setAccountType("savings")}
                  >
                    Savings Account
                  </button>
                  <button
                    type="button"
                    className={`radio-pill ${accountType === "current" ? "active" : ""}`}
                    onClick={() => setAccountType("current")}
                  >
                    Current Account
                  </button>
                </div>
              </div>

              <div className="sandbox-notice-pill mb-3">
                <ShieldCheck size={15} className="text-teal" />
                <span>Sandbox Verification: Account verified via simulated NPCI penny drop API.</span>
              </div>

              <div className="modal-actions-row">
                <button
                  type="button"
                  className="secondary-action-btn"
                  onClick={() => setView("list")}
                  disabled={submitting}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-action-btn flex-1" disabled={submitting}>
                  {submitting ? "Verifying with NPCI..." : "Link Bank Account"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
