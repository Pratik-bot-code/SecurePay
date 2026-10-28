import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Banknote,
  Bell,
  Building2,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  Filter,
  History,
  Home,
  KeyRound,
  Lock,
  LogOut,
  Menu,
  MoreHorizontal,
  Plus,
  QrCode,
  Receipt,
  RefreshCw,
  Search,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Store,
  Trash2,
  UserRound,
  Wallet,
  WifiOff,
  X,
} from "lucide-react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { App as CapApp } from "@capacitor/app";
import { StatusBar, Style } from "@capacitor/status-bar";

import { api, apiRequest, setCsrfToken, toProfile } from "./api.js";
import AuthScreen from "./components/AuthScreen.jsx";
import Avatar from "./components/Avatar.jsx";
import BankAccountsModal from "./components/BankAccountsModal.jsx";
import DisputeHelpModal from "./components/DisputeHelpModal.jsx";
import MerchantDashboardModal from "./components/MerchantDashboardModal.jsx";
import ReceiveQRModal from "./components/ReceiveQRModal.jsx";
import SendPaymentModal from "./components/SendPaymentModal.jsx";
import TransactionReceiptModal from "./components/TransactionReceiptModal.jsx";
import TransactionLedger from "./components/TransactionLedger.jsx";

const NAV_GROUPS = [
  {
    label: "FINANCIALS",
    items: [
      { to: "/", label: "Dashboard", icon: Home, end: true },
      { to: "/transactions", label: "Transactions", icon: History },
      { to: "/banks", label: "Bank Accounts", icon: Building2 },
      { to: "/receive", label: "Receive Money", icon: QrCode },
      { to: "/merchant", label: "Merchant Hub", icon: Store },
    ],
  },
  {
    label: "SETTINGS",
    items: [
      { to: "/notifications", label: "Notifications", icon: Bell },
      { to: "/profile", label: "Profile", icon: UserRound },
      { to: "/security", label: "Security & Sessions", icon: ShieldCheck },
    ],
  },
];

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [toast, setToast] = useState("");

  // Modals
  const [showSendModal, setShowSendModal] = useState(false);
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showBankModal, setShowBankModal] = useState(false);
  const [showMerchantModal, setShowMerchantModal] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);

  const showToastMsg = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3500);
  };

  const loadSession = useCallback(async () => {
    try {
      const data = await apiRequest("/auth/session");
      if (data?.user) {
        setCurrentUser(data.user);
        if (data.csrf_token) setCsrfToken(data.csrf_token);
        const dashData = await api.getDashboard();
        setDashboard(dashData);
      } else {
        setCurrentUser(null);
      }
    } catch {
      setCurrentUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [deferredInstallPrompt, setDeferredInstallPrompt] = useState(null);
  const [isInstallable, setIsInstallable] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      showToastMsg("Back online. Synchronizing data...");
      refreshDashboard();
    };
    const handleOffline = () => {
      setIsOnline(false);
      showToastMsg("Network connection lost. Offline transactions disabled.");
    };
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    const handleBeforeInstall = (e) => {
      e.preventDefault();
      setDeferredInstallPrompt(e);
      setIsInstallable(true);
    };
    window.addEventListener("beforeinstallprompt", handleBeforeInstall);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
    };
  }, []);

  // Native Mobile Back Button & Status Bar Integration
  useEffect(() => {
    try {
      StatusBar.setStyle({ style: Style.Dark }).catch(() => {});
      StatusBar.setBackgroundColor({ color: "#0A192F" }).catch(() => {});
    } catch {}

    let backListener = null;
    try {
      backListener = CapApp.addListener("backButton", ({ canGoBack }) => {
        if (showSendModal) { setShowSendModal(false); return; }
        if (showReceiveModal) { setShowReceiveModal(false); return; }
        if (showBankModal) { setShowBankModal(false); return; }
        if (showMerchantModal) { setShowMerchantModal(false); return; }
        if (showHelpModal) { setShowHelpModal(false); return; }
        if (selectedTx) { setSelectedTx(null); return; }
        if (mobileMenuOpen) { setMobileMenuOpen(false); return; }
        if (canGoBack) {
          window.history.back();
        } else {
          CapApp.exitApp();
        }
      });
    } catch {}

    return () => {
      if (backListener) {
        backListener.then((h) => h?.remove?.()).catch(() => {});
      }
    };
  }, [showSendModal, showReceiveModal, showBankModal, showMerchantModal, showHelpModal, selectedTx, mobileMenuOpen]);

  const handleInstallApp = async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    const choice = await deferredInstallPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setIsInstallable(false);
      showToastMsg("SecurePay installation initiated.");
    }
    setDeferredInstallPrompt(null);
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {}
    setCurrentUser(null);
    setDashboard(null);
  };

  const refreshDashboard = async () => {
    try {
      const dashData = await api.getDashboard();
      setDashboard(dashData);
    } catch {}
  };

  if (loading) {
    return (
      <div className="app-loading-screen">
        <div className="brand-icon spin-subtle">
          <ShieldCheck size={28} />
        </div>
        <p className="mt-3 text-muted font-medium">Securing session...</p>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <AuthScreen
        onAuthenticated={(userData, token) => {
          setCurrentUser(userData);
          if (token) setCsrfToken(token);
          loadSession();
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileMenuOpen ? "mobile-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={22} />
          </div>
          <div className="brand-name">
            Secure<span>Pay</span>
            <small>FINTECH PLATFORM</small>
          </div>
        </div>

        <div className="sidebar-demo">
          <span className="demo-dot" />
          <span>NPCI Sandbox Active</span>
        </div>

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="nav-group">
              <p className="nav-label">{group.label}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                    {item.to === "/notifications" && dashboard?.notifications_unread > 0 && (
                      <span className="nav-count">{dashboard.notifications_unread}</span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          {isInstallable && (
            <div className="install-app-card" onClick={handleInstallApp}>
              <div className="install-icon">
                <Smartphone size={18} />
              </div>
              <div>
                <strong>Install App</strong>
                <p>Add SecurePay to home screen</p>
              </div>
            </div>
          )}

          <div className="help-card" onClick={() => setShowHelpModal(true)}>
            <div className="help-icon">
              <ShieldAlert size={18} />
            </div>
            <div>
              <strong>Dispute & Support</strong>
              <p>24/7 payment assistance</p>
            </div>
          </div>

          <div className="profile-switch">
            <Avatar name={currentUser.display_name} handle={currentUser.demo_handle} size={32} />
            <div className="profile-switch-copy">
              <strong>{currentUser.display_name}</strong>
              <small>@{currentUser.demo_handle}</small>
            </div>
            <button className="icon-btn-danger" onClick={handleLogout} title="Sign Out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-column">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-btn d-md-none"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Navigation"
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              <span>SecurePay</span>
              <span>/</span>
              <strong>Fintech Suite</strong>
            </div>
          </div>

          <div className="topbar-actions">
            {isInstallable && (
              <button className="secondary-action-btn install-btn" onClick={handleInstallApp}>
                <Smartphone size={15} />
                <span className="d-none d-sm-inline">Install App</span>
              </button>
            )}
            <button className="primary-action-btn" onClick={() => setShowSendModal(true)}>
              <Send size={15} />
              <span className="d-none d-sm-inline">Pay / Transfer</span>
            </button>
            <button className="secondary-action-btn" onClick={() => setShowReceiveModal(true)}>
              <QrCode size={15} />
              <span className="d-none d-sm-inline">Receive QR</span>
            </button>
          </div>
        </header>

        {!isOnline && (
          <div className="offline-banner animate-fade-in">
            <WifiOff size={16} />
            <span>Internet connection lost. Financial transactions and balance queries are disabled for security.</span>
          </div>
        )}

        {toast && <div className="floating-toast">{toast}</div>}

        <main className="content-wrap">
          <Routes>
            <Route
              path="/"
              element={
                <DashboardView
                  user={currentUser}
                  dashboard={dashboard}
                  onOpenSend={() => setShowSendModal(true)}
                  onOpenReceive={() => setShowReceiveModal(true)}
                  onOpenBank={() => setShowBankModal(true)}
                  onOpenMerchant={() => setShowMerchantModal(true)}
                  onSelectTransaction={(tx) => setSelectedTx(tx)}
                />
              }
            />
            <Route
              path="/transactions"
              element={
                <TransactionLedger
                  onSelectTransaction={(tx) => setSelectedTx(tx)}
                />
              }
            />
            <Route
              path="/banks"
              element={
                <BankAccountsView
                  onAccountUpdated={refreshDashboard}
                />
              }
            />
            <Route
              path="/receive"
              element={
                <ReceivePageView user={currentUser} />
              }
            />
            <Route
              path="/merchant"
              element={
                <MerchantView />
              }
            />
            <Route
              path="/notifications"
              element={
                <NotificationsView
                  onNotificationUpdated={refreshDashboard}
                />
              }
            />
            <Route
              path="/profile"
              element={
                <ProfileView
                  user={currentUser}
                  onProfileUpdated={(updated) => {
                    setCurrentUser(updated);
                    showToastMsg("Profile details updated successfully.");
                  }}
                />
              }
            />
            <Route
              path="/security"
              element={
                <SecurityView
                  user={currentUser}
                  onToast={showToastMsg}
                />
              }
            />
            <Route
              path="*"
              element={
                <DashboardView
                  user={currentUser}
                  dashboard={dashboard}
                  onOpenSend={() => setShowSendModal(true)}
                  onOpenReceive={() => setShowReceiveModal(true)}
                  onOpenBank={() => setShowBankModal(true)}
                  onOpenMerchant={() => setShowMerchantModal(true)}
                  onSelectTransaction={(tx) => setSelectedTx(tx)}
                />
              }
            />
          </Routes>
        </main>
      </div>

      {/* Global Interactive Modals */}
      <SendPaymentModal
        isOpen={showSendModal}
        onClose={() => setShowSendModal(false)}
        balancePaise={dashboard?.account?.balance_paise || 0}
        onPaymentSuccess={refreshDashboard}
      />
      <ReceiveQRModal
        isOpen={showReceiveModal}
        onClose={() => setShowReceiveModal(false)}
        user={currentUser}
      />
      <BankAccountsModal
        isOpen={showBankModal}
        onClose={() => setShowBankModal(false)}
        onAccountUpdated={refreshDashboard}
      />
      <MerchantDashboardModal
        isOpen={showMerchantModal}
        onClose={() => setShowMerchantModal(false)}
      />
      <DisputeHelpModal
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
      />
      <TransactionReceiptModal
        isOpen={Boolean(selectedTx)}
        onClose={() => setSelectedTx(null)}
        transaction={selectedTx}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 1: Dashboard
// ---------------------------------------------------------------------------
function DashboardView({ user, dashboard, onOpenSend, onOpenReceive, onOpenBank, onOpenMerchant, onSelectTransaction }) {
  const [balanceVisible, setBalanceVisible] = useState(true);

  const balancePaise = dashboard?.account?.balance_paise || 0;
  const balanceRupees = (balancePaise / 100).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div className="dashboard-page animate-fade-in">
      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user.display_name}</h1>
        <p className="page-subtitle">Unified accounts, UPI payments & real-time double-entry ledger</p>
      </div>

      {/* Primary Balance Hero Card */}
      <div className="hero-balance-card">
        <div className="balance-top-row">
          <div className="balance-label-wrap">
            <Wallet size={16} />
            <span className="balance-label">TOTAL AVAILABLE BALANCE</span>
          </div>
          <button
            className="eye-toggle-btn"
            onClick={() => setBalanceVisible(!balanceVisible)}
            title={balanceVisible ? "Hide balance" : "Show balance"}
          >
            {balanceVisible ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        <div className="balance-amount-row">
          <span className="currency-sign">₹</span>
          <span className="balance-number">{balanceVisible ? balanceRupees : "••••••"}</span>
        </div>

        <div className="hero-actions-row">
          <button className="hero-action-pill teal-pill" onClick={onOpenSend}>
            <Send size={15} />
            <span>Pay & Transfer</span>
          </button>
          <button className="hero-action-pill" onClick={onOpenReceive}>
            <QrCode size={15} />
            <span>Receive QR</span>
          </button>
          <button className="hero-action-pill" onClick={onOpenBank}>
            <Building2 size={15} />
            <span>Link Bank</span>
          </button>
          <button className="hero-action-pill" onClick={onOpenMerchant}>
            <Store size={15} />
            <span>Merchant Hub</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-head">
            <span className="stat-head-title">MONTHLY SPEND</span>
            <div className="stat-head-icon">
              <ArrowUpRight size={17} />
            </div>
          </div>
          <h3 className="stat-value">₹{((dashboard?.monthly_spend_paise || 0) / 100).toFixed(2)}</h3>
          <p className="stat-subtext">Current calendar month</p>
        </div>

        <div className="stat-card">
          <div className="stat-head">
            <span className="stat-head-title">TOTAL RECEIVED</span>
            <div className="stat-head-icon">
              <ArrowDownLeft size={17} />
            </div>
          </div>
          <h3 className="stat-value text-teal">₹{((dashboard?.total_received_paise || 0) / 100).toFixed(2)}</h3>
          <p className="stat-subtext">All verified credits</p>
        </div>

        <div className="stat-card">
          <div className="stat-head">
            <span className="stat-head-title">COMPLETED TRANSACTIONS</span>
            <div className="stat-head-icon">
              <History size={17} />
            </div>
          </div>
          <h3 className="stat-value">{dashboard?.transaction_count || 0}</h3>
          <p className="stat-subtext">Immutable ledger entries</p>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="content-card">
        <div className="card-title-row">
          <h2 className="card-title">Recent Transactions</h2>
          <NavLink to="/transactions" className="view-all-link">
            <span>View All</span>
            <ChevronRight size={14} />
          </NavLink>
        </div>

        {dashboard?.recent_transactions?.length > 0 ? (
          <div className="transactions-list">
            {dashboard.recent_transactions.map((tx) => (
              <div
                key={tx.reference}
                className="transaction-row-card"
                onClick={() => onSelectTransaction(tx)}
              >
                <div className="tx-left">
                  <div className={`tx-icon-circle ${tx.signed_amount_paise > 0 ? "credit" : "debit"}`}>
                    {tx.signed_amount_paise > 0 ? <ArrowDownLeft size={18} /> : <ArrowUpRight size={18} />}
                  </div>
                  <div className="tx-info">
                    <h4 className="tx-name">{tx.name}</h4>
                    <div className="tx-meta">
                      <span>{tx.category}</span>
                      <span>•</span>
                      <span>{new Date(tx.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="tx-right">
                  <p className={`tx-amount ${tx.signed_amount_paise > 0 ? "credit" : "debit"}`}>
                    {tx.signed_amount_paise > 0 ? "+" : "-"}₹{(Math.abs(tx.amount_paise) / 100).toFixed(2)}
                  </p>
                  <span className="tx-status-badge completed">COMPLETED</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state-box">
            <History size={40} className="text-muted" />
            <h4>No transactions yet</h4>
            <p>Make your first payment or scan your QR code to receive sandbox funds.</p>
            <button className="primary-action-btn mt-2" onClick={onOpenSend}>
              <Send size={15} />
              <span>Make a Payment</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}



// ---------------------------------------------------------------------------
// VIEW 3: Bank Accounts
// ---------------------------------------------------------------------------
function BankAccountsView({ onAccountUpdated }) {
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const loadBanks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getLinkedBanks();
      setBanks(data || []);
    } catch {
      setBanks([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBanks();
  }, [loadBanks]);

  return (
    <div className="banks-page animate-fade-in">
      <div className="page-heading d-flex justify-between align-center">
        <div>
          <h1 className="page-title">Linked Bank Accounts</h1>
          <p className="page-subtitle">Manage settlement accounts for instant UPI payouts and funding</p>
        </div>
        <button className="primary-action-btn" onClick={() => setShowAddModal(true)}>
          <Plus size={16} />
          <span>Add Bank Account</span>
        </button>
      </div>

      <div className="content-card">
        {loading ? (
          <div className="skeleton-loading-wrap">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        ) : banks.length > 0 ? (
          <div className="bank-cards-grid">
            {banks.map((bank) => (
              <div key={bank.id} className={`bank-item-card ${bank.is_primary ? "primary-bank" : ""}`}>
                <div className="bank-item-icon">
                  <Building2 size={24} />
                </div>
                <div className="bank-item-details">
                  <div className="bank-name-row">
                    <strong className="bank-name">{bank.bank_name}</strong>
                    {bank.is_primary && <span className="primary-tag">Primary Account</span>}
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
                    <span>NPCI Verification Active</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state-box">
            <Building2 size={40} className="text-muted" />
            <h4>No bank accounts linked yet</h4>
            <p>Link your bank account to enable direct payouts and UPI interoperability.</p>
            <button className="primary-action-btn mt-2" onClick={() => setShowAddModal(true)}>
              <Plus size={16} />
              <span>Link Account Now</span>
            </button>
          </div>
        )}
      </div>

      <BankAccountsModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAccountUpdated={() => {
          loadBanks();
          if (onAccountUpdated) onAccountUpdated();
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 4: Receive Page
// ---------------------------------------------------------------------------
function ReceivePageView({ user }) {
  const [copied, setCopied] = useState(false);
  const [customAmount, setCustomAmount] = useState("");
  const handle = user?.demo_handle || "user";
  const upiId = `${handle}@securepay`;
  
  const amountPaise = customAmount && !isNaN(customAmount) ? Math.round(parseFloat(customAmount) * 100) : 0;
  const upiUrl = amountPaise > 0
    ? `upi://pay?pa=${upiId}&pn=${encodeURIComponent(user?.display_name || handle)}&am=${(amountPaise / 100).toFixed(2)}&cu=INR`
    : `upi://pay?pa=${upiId}&pn=${encodeURIComponent(user?.display_name || handle)}&cu=INR`;

  const copyUpi = () => {
    navigator.clipboard.writeText(upiId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyLink = () => {
    navigator.clipboard.writeText(upiUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="receive-page animate-fade-in">
      <div className="page-heading">
        <h1 className="page-title">Receive Money</h1>
        <p className="page-subtitle">Scan QR or share your personal UPI ID</p>
      </div>

      <div className="content-card max-w-lg mx-auto text-center">
        <div className="qr-container">
          <div className="qr-badge-banner">
            <Sparkles size={14} />
            <span>Instant Sandbox Settlement</span>
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

          <h3 className="qr-user-name">{user?.display_name}</h3>
          <div className="upi-id-pill" onClick={copyUpi} title="Click to copy UPI ID">
            <span className="upi-id-text">{upiId}</span>
            <button className="copy-btn">
              {copied ? <Check size={14} className="text-teal" /> : <Copy size={14} />}
            </button>
          </div>
          {copied && <span className="copied-toast">Copied to clipboard!</span>}

          <div className="qr-amount-section mt-4">
            <label htmlFor="receive-page-amount" className="input-label">
              Set specific amount (optional)
            </label>
            <div className="currency-input-wrap">
              <span className="currency-symbol">₹</span>
              <input
                id="receive-page-amount"
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

          <div className="qr-actions-row mt-4">
            <button className="secondary-action-btn flex-1" onClick={copyLink}>
              <Copy size={15} />
              <span>Copy Payment Link</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 5: Merchant Hub
// ---------------------------------------------------------------------------
function MerchantView() {
  const [showModal, setShowModal] = useState(false);
  const [merchant, setMerchant] = useState(null);

  useEffect(() => {
    api.getMerchantProfile().then(setMerchant).catch(() => setMerchant(null));
  }, []);

  return (
    <div className="merchant-page animate-fade-in">
      <div className="page-heading">
        <h1 className="page-title">Merchant Hub</h1>
        <p className="page-subtitle">Storefront checkout, merchant QR & settlement APIs</p>
      </div>

      <div className="content-card">
        {merchant ? (
          <div className="merchant-active-card">
            <div className="merchant-meta-top">
              <span className="merchant-badge-active">
                <CheckCircle2 size={14} />
                <span>ACTIVE STOREFRONT</span>
              </span>
              <span className="font-mono text-muted">{merchant.merchant_code}</span>
            </div>
            <h2 className="merchant-title">{merchant.business_name}</h2>
            <p className="text-muted">{merchant.category}</p>
            <div className="upi-handle-row">
              <span className="text-muted">Business UPI:</span>
              <code className="text-teal font-bold">{merchant.upi_handle}</code>
            </div>
            <button className="primary-action-btn mt-4" onClick={() => setShowModal(true)}>
              <Store size={16} />
              <span>View Storefront QR & Settings</span>
            </button>
          </div>
        ) : (
          <div className="empty-state-box">
            <Store size={44} className="text-teal" />
            <h4>Activate Merchant Solutions</h4>
            <p>Accept customer payments in-store and online with 0% MDR transaction fees.</p>
            <button className="primary-action-btn mt-2" onClick={() => setShowModal(true)}>
              <Plus size={16} />
              <span>Register as Merchant</span>
            </button>
          </div>
        )}
      </div>

      <MerchantDashboardModal
        isOpen={showModal}
        onClose={() => {
          setShowModal(false);
          api.getMerchantProfile().then(setMerchant).catch(() => setMerchant(null));
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 6: Notifications
// ---------------------------------------------------------------------------
function NotificationsView({ onNotificationUpdated }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getNotifications();
      setNotifications(data || []);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      await loadNotifications();
      if (onNotificationUpdated) onNotificationUpdated();
    } catch {}
  };

  const handleToggleRead = async (id, currentUnread) => {
    try {
      await api.markNotificationRead(id, currentUnread);
      await loadNotifications();
      if (onNotificationUpdated) onNotificationUpdated();
    } catch {}
  };

  return (
    <div className="notifications-page animate-fade-in">
      <div className="page-heading d-flex justify-between align-center">
        <div>
          <h1 className="page-title">Notifications</h1>
          <p className="page-subtitle">Security alerts and transaction updates</p>
        </div>
        {notifications.some((n) => n.unread) && (
          <button className="secondary-action-btn" onClick={handleMarkAllRead}>
            <Check size={15} />
            <span>Mark All as Read</span>
          </button>
        )}
      </div>

      <div className="content-card">
        {loading ? (
          <div className="skeleton-loading-wrap">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        ) : notifications.length > 0 ? (
          <div className="notifications-list">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`notification-row ${n.unread ? "unread" : ""}`}
                onClick={() => handleToggleRead(n.id, n.unread)}
              >
                <div className="n-icon">
                  <Bell size={18} />
                </div>
                <div className="n-content">
                  <div className="n-title-row">
                    <strong>{n.title}</strong>
                    {n.unread && <span className="unread-dot" />}
                  </div>
                  <p className="n-body">{n.body}</p>
                  <small className="n-time">{new Date(n.created_at).toLocaleString()}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state-box">
            <Bell size={40} className="text-muted" />
            <h4>All caught up!</h4>
            <p>You have no notifications or alerts at this time.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 7: Profile
// ---------------------------------------------------------------------------
function ProfileView({ user, onProfileUpdated }) {
  const [editing, setEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [handle, setHandle] = useState(user.demo_handle);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateProfile({
        display_name: displayName,
        demo_handle: handle,
      });
      setEditing(false);
      onProfileUpdated(updated);
    } catch (err) {
      setError(err.message || "Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  const memberSince = user.created_at
    ? new Date(user.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" })
    : "Recently";

  return (
    <div className="profile-page animate-fade-in">
      <div className="page-heading">
        <h1 className="page-title">Personal Profile</h1>
        <p className="page-subtitle">Account details, unique handle & verification tier</p>
      </div>

      {error && (
        <div className="alert-banner alert-error">
          <span>{error}</span>
        </div>
      )}

      <div className="content-card">
        {!editing ? (
          <div className="profile-details-view">
            <div className="profile-avatar-row">
              <Avatar name={user.display_name} handle={user.demo_handle} size={56} />
              <div>
                <h2>{user.display_name}</h2>
                <code className="text-teal font-bold">@{user.demo_handle}</code>
              </div>
              <button className="secondary-action-btn ml-auto" onClick={() => setEditing(true)}>
                Edit Profile
              </button>
            </div>

            <div className="profile-fields-grid mt-4">
              <div className="p-field">
                <span className="p-label">Account Role</span>
                <span className="p-val">{user.role.toUpperCase()}</span>
              </div>
              <div className="p-field">
                <span className="p-label">Verification Status</span>
                <span className="p-val text-teal font-semibold">Active & Verified</span>
              </div>
              <div className="p-field">
                <span className="p-label">Member Since</span>
                <span className="p-val">{memberSince}</span>
              </div>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSave} className="profile-edit-form">
            <div className="form-group">
              <label className="input-label">Display Name</label>
              <input
                type="text"
                className="form-input"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="input-label">Profile Handle (@)</label>
              <input
                type="text"
                className="form-input"
                value={handle}
                onChange={(e) => setHandle(e.target.value)}
                required
              />
            </div>
            <div className="form-actions-row">
              <button
                type="button"
                className="secondary-action-btn"
                onClick={() => setEditing(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button type="submit" className="primary-action-btn" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VIEW 8: Security & Sessions
// ---------------------------------------------------------------------------
function SecurityView({ user, onToast }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getSessions();
      setSessions(data || []);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleRevoke = async (id) => {
    try {
      await api.revokeSession(id);
      onToast("Remote session revoked successfully.");
      await loadSessions();
    } catch (err) {
      onToast(err.message || "Failed to revoke session.");
    }
  };

  return (
    <div className="security-page animate-fade-in">
      <div className="page-heading">
        <h1 className="page-title">Security & Sessions</h1>
        <p className="page-subtitle">Cryptographic protections, active devices, and credentials</p>
      </div>

      <div className="content-card mb-4">
        <div className="card-title-row">
          <h2 className="card-title">Authentication & Password</h2>
          <button className="primary-action-btn" onClick={() => setShowPasswordModal(true)}>
            <KeyRound size={15} />
            <span>Change Password</span>
          </button>
        </div>
        <p className="text-muted text-sm">
          Passwords are protected using Argon2id cryptographic hashing. Updating your password automatically revokes all other active sessions across devices.
        </p>
      </div>

      <div className="content-card">
        <h2 className="card-title mb-3">Active Connected Sessions ({sessions.length})</h2>
        {loading ? (
          <div className="skeleton-loading-wrap">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        ) : (
          <div className="sessions-list">
            {sessions.map((s) => (
              <div key={s.id} className={`session-row ${s.current ? "current-device" : ""}`}>
                <div className="session-icon">
                  <ShieldCheck size={20} className={s.current ? "text-teal" : "text-muted"} />
                </div>
                <div className="session-details">
                  <div className="session-label-row">
                    <strong>{s.label}</strong>
                    {s.current && <span className="primary-tag">Current Session</span>}
                  </div>
                  <div className="session-meta">
                    <span>Started: {new Date(s.created_at).toLocaleString()}</span>
                    <span>•</span>
                    <span>Last active: {new Date(s.last_seen_at).toLocaleString()}</span>
                  </div>
                </div>
                {!s.current && (
                  <button
                    className="icon-btn-danger"
                    onClick={() => handleRevoke(s.id)}
                    title="Revoke session"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showPasswordModal && (
        <PasswordChangeModal
          onClose={() => setShowPasswordModal(false)}
          onSuccess={() => {
            setShowPasswordModal(false);
            onToast("Password updated. Other sessions revoked.");
            loadSessions();
          }}
        />
      )}
    </div>
  );
}

function PasswordChangeModal({ onClose, onSuccess }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      onSuccess();
    } catch (err) {
      setError(err.message || "Failed to update password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <div className="modal-icon-badge">
              <KeyRound size={20} />
            </div>
            <div>
              <h3 className="modal-title">Change Account Password</h3>
              <p className="modal-subtitle">Minimum 12 characters, high entropy</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}><X size={18} /></button>
        </div>

        {error && <div className="alert-banner alert-error"><span>{error}</span></div>}

        <form onSubmit={handleSubmit} className="modal-body-scroll">
          <div className="form-group">
            <label className="input-label">Current Password</label>
            <div className="password-input-wrap">
              <input
                type={showCurrentPassword ? "text" : "password"}
                className="form-input"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                title={showCurrentPassword ? "Hide password" : "Show password"}
                aria-label={showCurrentPassword ? "Hide password" : "Show password"}
              >
                {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          <div className="form-group">
            <label className="input-label">New Password (12+ chars)</label>
            <div className="password-input-wrap">
              <input
                type={showNewPassword ? "text" : "password"}
                className="form-input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={12}
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowNewPassword(!showNewPassword)}
                title={showNewPassword ? "Hide password" : "Show password"}
                aria-label={showNewPassword ? "Hide password" : "Show password"}
              >
                {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <small className="field-hint">Must contain varied characters; cannot be purely numeric or common words.</small>
          </div>
          <div className="modal-actions-row">
            <button type="button" className="secondary-action-btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-action-btn" disabled={submitting}>
              {submitting ? "Updating..." : "Update Password"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
