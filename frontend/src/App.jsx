import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  Banknote,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Copy,
  CircleDollarSign,
  CreditCard,
  Download,
  Droplets,
  Fingerprint,
  Filter,
  Gift,
  History,
  Home,
  KeyRound,
  LockKeyhole,
  LogOut,
  Menu,
  MoreHorizontal,
  QrCode,
  Receipt,
  ReceiptText,
  Search,
  Send,
  Settings2,
  Shield,
  ShieldCheck,
  Sparkles,
  Smartphone,
  UserRound,
  Tv,
  Wallet,
  Wifi,
  Zap,
  X,
} from "lucide-react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Avatar from "./components/Avatar.jsx";
import AuthScreen from "./components/AuthScreen.jsx";
import Modal from "./components/Modal.jsx";
import PageHeading from "./components/PageHeading.jsx";
import { apiRequest, setCsrfToken, toProfile } from "./api.js";

const navGroups = [
  {
    label: "MENU",
    items: [
      { to: "/", label: "Overview", icon: Home, end: true },
      { to: "/transactions", label: "Transactions", icon: History },
      { to: "/services", label: "Bills & services", icon: Receipt },
      { to: "/receive", label: "Receive money", icon: QrCode },
      { to: "/notifications", label: "Notifications", icon: Bell },
    ],
  },
  {
    label: "PREFERENCES",
    items: [
      { to: "/profile", label: "Profile", icon: UserRound },
      { to: "/security", label: "Security", icon: ShieldCheck },
    ],
  },
];

function App() {
  const [authStatus, setAuthStatus] = useState("loading");
  const [notifications, setNotifications] = useState([]);
  const [preferences, setPreferences] = useState({ biometric_preference: false, security_alerts: true });
  const [sessions, setSessions] = useState([]);
  const [modal, setModal] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [showServiceNotice, setShowServiceNotice] = useState(true);
  const [profile, setProfile] = useState({ name: "", handle: "" });
  const [toast, setToast] = useState("");
  const [backendError, setBackendError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  const unreadCount = notifications.filter((item) => item.unread).length;
  const routeStyle = {
    "/": "overview",
    "/transactions": "transactions",
    "/services": "services",
    "/receive": "receive",
    "/notifications": "notifications",
    "/profile": "profile",
    "/security": "security",
  }[location.pathname] || "overview";

  const refreshData = useCallback(async () => {
    const [dashboard, notificationRows, preferenceData, sessionRows] = await Promise.all([
      apiRequest("/dashboard"),
      apiRequest("/notifications"),
      apiRequest("/preferences"),
      apiRequest("/auth/sessions"),
    ]);
    setProfile(toProfile(dashboard.user));
    setNotifications(notificationRows
      .filter((item) => item.icon !== "receipt" && !/\b(demo|simulated)\b/i.test(`${item.title} ${item.body}`))
      .map((item) => ({
        id: item.id,
        title: item.title.replace(/\bdemo\b/gi, "SecurePay"),
        body: item.body.replace(/\bdemo\b/gi, "SecurePay"),
        time: new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at)),
        unread: item.unread,
        icon: item.icon,
      })));
    setPreferences(preferenceData);
    setSessions(sessionRows);
    setAuthStatus("authenticated");
  }, []);

  useEffect(() => {
    let active = true;
    apiRequest("/auth/session")
      .then(async (session) => {
        if (!active) return;
        await refreshData();
      })
      .catch((error) => {
        if (!active) return;
        if (error.statusCode === 401) {
          setAuthStatus("signed-out");
        } else {
          setAuthStatus("unavailable");
          setBackendError(error.message);
        }
      });
    return () => { active = false; };
  }, [refreshData]);

  const handleAuthenticated = async () => {
    setBackendError("");
    try {
      await refreshData();
    } catch (error) {
      setBackendError(error.message);
      setAuthStatus("unavailable");
    }
  };

  const signOut = async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch (error) {
      showToast(`Could not sign out: ${error.message}`);
      return;
    }
    setCsrfToken("");
    setProfile({ name: "", handle: "" });
    setAuthStatus("signed-out");
    setNotifications([]);
    navigate("/");
  };

  const showToast = (message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  };

  const closeModal = () => {
    setModal(null);
  };

  const openPaymentStatus = () => setModal("payments");
  const openBankLinking = () => setModal("bank");
  const routeTitle = useMemo(() => {
    const current = navGroups.flatMap((group) => group.items).find((item) => item.to === location.pathname);
    if (current) return current.label;
    if (location.pathname === "/") return "Overview";
    return "SecurePay";
  }, [location.pathname]);

  if (authStatus === "loading") {
    return <div className="auth-loading" role="status"><span className="brand-icon"><Wallet size={20} /></span><strong>Connecting to SecurePay…</strong></div>;
  }
  if (authStatus === "signed-out") {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }
  if (authStatus === "unavailable") {
    return <main className="auth-loading"><strong>SecurePay backend unavailable</strong><p>{backendError}</p><button className="button button-outline" onClick={() => window.location.reload()}>Try again</button></main>;
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? "sidebar-open" : ""}`}>
        <Brand />
        <div className="sidebar-demo"><span className="demo-dot" /> Payments not connected</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p className="nav-label">{group.label}</p>
              {group.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                >
                  <Icon size={18} strokeWidth={1.8} />
                  <span>{label}</span>
                  {label === "Notifications" && unreadCount > 0 && <span className="nav-count">{unreadCount}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="help-card">
            <div className="help-icon"><CircleHelp size={18} /></div>
            <div><strong>Need a hand?</strong><p>We’re here to help.</p></div>
            <button className="icon-button tiny" aria-label="Open help" onClick={() => setModal("help")}><ArrowRight size={16} /></button>
          </div>
          <button className="profile-switch" onClick={() => navigate("/profile")}>
            <Avatar name={profile.name} color="peach" />
            <span className="profile-switch-copy"><strong>{profile.name}</strong><small>Personal account</small></span>
            <MoreHorizontal size={19} className="muted-icon" />
          </button>
        </div>
      </aside>

      {mobileNavOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}

      <main className="main-column">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={21} /></button>
            <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><strong>{routeTitle}</strong></div>
          </div>
          <div className="topbar-actions">
            <div className="header-demo"><span className="demo-dot" /> NOT CONNECTED</div>
            <button className="icon-button notification-button" aria-label={`${unreadCount} unread notifications`} onClick={() => navigate("/notifications")}>
              <Bell size={19} />{unreadCount > 0 && <span className="notification-dot" />}
            </button>
            <button className="top-avatar-button" onClick={() => navigate("/profile")} aria-label="Go to profile"><Avatar name={profile.name} color="peach" /></button>
            <button className="topbar-signout" onClick={signOut}><LogOut size={16} /><span>Sign out</span></button>
          </div>
        </header>

        <div className={`content-wrap route-${routeStyle}`}>
          {showServiceNotice && <div className="demo-banner">
            <div className="banner-mark"><Sparkles size={15} /></div>
            <p><strong>Payment services are not connected.</strong> Balances and transfers are unavailable, and no funds move through SecurePay. Do not enter banking credentials.</p>
            <button className="banner-dismiss" aria-label="Dismiss service status notice" onClick={() => setShowServiceNotice(false)}><X size={16} /></button>
          </div>}
          <Routes>
            <Route path="/" element={<Dashboard profile={profile} onPaymentStatus={openPaymentStatus} onServices={() => navigate("/services")} onBankLinking={openBankLinking} onActivity={() => navigate("/transactions")} />} />
            <Route path="/transactions" element={<TransactionsPage />} />
            <Route path="/services" element={<ServicesPage onSelect={() => setModal("provider")} onRewards={() => setModal("rewards")} />} />
            <Route path="/receive" element={<ReceivePage />} />
            <Route path="/notifications" element={<NotificationsPage notifications={notifications} onRefresh={refreshData} onError={showToast} />} />
            <Route path="/profile" element={<ProfilePage profile={profile} setProfile={setProfile} onToast={showToast} />} />
            <Route path="/security" element={<SecurityPage preferences={preferences} sessions={sessions} setPreferences={setPreferences} setSessions={setSessions} onChangePassword={() => setModal("password")} onToast={showToast} />} />
            <Route path="*" element={<Dashboard profile={profile} onPaymentStatus={openPaymentStatus} onServices={() => navigate("/services")} onBankLinking={openBankLinking} onActivity={() => navigate("/transactions")} />} />
          </Routes>
          <footer className="app-footer"><span>© {new Date().getFullYear()} SecurePay</span><span><Shield size={13} /> Payment services not connected</span><button className="footer-help" onClick={() => setModal("help")}>Help</button><button className="footer-help" onClick={signOut}>Sign out</button></footer>
        </div>
      </main>

      {modal === "help" && <HelpModal onClose={closeModal} onNavigate={(path) => { closeModal(); navigate(path); }} />}
      {modal === "password" && <PasswordModal onClose={closeModal} onComplete={(response) => { setCsrfToken(response.csrf_token); closeModal(); refreshData().catch((error) => showToast(error.message)); showToast("Password changed. Other sessions were signed out."); }} />}
      {modal === "payments" && <CapabilityModal title="Payments unavailable" eyebrow="PROVIDER NOT CONNECTED" onClose={closeModal}>SecurePay cannot send, receive, or scan payments until an approved payment provider is integrated. No funds have moved.</CapabilityModal>}
      {modal === "bank" && <CapabilityModal title="Bank account linking" eyebrow="NOT CONNECTED" onClose={closeModal}>SecurePay cannot connect to banks or retrieve bank balances. No bank account is linked, and you should never enter bank credentials here.</CapabilityModal>}
      {modal === "provider" && <CapabilityModal title="Bill payment unavailable" eyebrow="PROVIDER NOT CONNECTED" onClose={closeModal}>Billers and payment providers are not connected. This screen cannot recharge a phone, pay a bill, or debit your balance.</CapabilityModal>}
      {modal === "rewards" && <CapabilityModal title="Rewards unavailable" eyebrow="NOT CONFIGURED" onClose={closeModal}>There is no rewards program or reward balance connected to this account.</CapabilityModal>}
      {toast && <div className="toast" role="status"><CheckCircle2 size={18} />{toast}</div>}
    </div>
  );
}

function Brand() {
  return <a className="brand" href="/" aria-label="SecurePay overview">
    <span className="brand-icon"><Wallet size={20} strokeWidth={2.2} /></span>
    <span className="brand-name">secure<span>pay</span><small>PAYMENTS, SIMPLIFIED</small></span>
  </a>;
}

function Dashboard({ profile, onPaymentStatus, onServices, onBankLinking, onActivity }) {
  const navigate = useNavigate();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const now = new Date();
  return <>
    <PageHeading eyebrow={new Intl.DateTimeFormat("en-IN", { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(now).toUpperCase()} title={`${greeting}, ${profile.name.split(" ")[0]}`} description="Your SecurePay account overview." action={<button className="button button-outline hide-mobile" onClick={onActivity}>Transaction history <ChevronDown size={15} /></button>} />
    <section className="dashboard-grid dashboard-readiness-grid">
      <div className="balance-card">
        <div className="balance-card-top"><span><span className="balance-icon"><Wallet size={17} /></span> Bank balance</span><span className="not-connected-pill">NOT CONNECTED</span></div>
        <div className="balance-amount balance-unavailable">Unavailable</div>
        <p className="balance-caption">No bank or payment provider is connected to this account.</p>
        <div className="balance-divider" />
        <div className="balance-actions">
          <button className="button button-white" onClick={onBankLinking}><Banknote size={16} /> Bank linking status <ArrowRight size={15} /></button>
          <button className="button button-glass" onClick={onPaymentStatus}><ShieldCheck size={17} /> Payment status</button>
        </div>
        <div className="balance-orb orb-one" /><div className="balance-orb orb-two" />
      </div>
      <div className="spend-card">
        <div className="card-heading"><div><p className="eyebrow">ACCOUNT SETUP</p><h2>Payments are not active</h2></div><span className="service-tile-icon"><ShieldCheck size={19} /></span></div>
        <p className="spend-subtitle">Payment features become available after approved provider integration, verification, and compliance setup.</p>
        <div className="service-disclosure"><ShieldCheck size={18} /><p><strong>No real payments can be made or received.</strong> Do not rely on this account for bank balances or financial records.</p></div>
      </div>
    </section>
    <section className="quick-section">
      <div className="section-title-row"><div><p className="eyebrow">MAKE IT HAPPEN</p><h2>Quick actions</h2></div><button className="text-button" onClick={() => navigate("/transactions")}>Transaction history <ArrowRight size={15} /></button></div>
      <div className="quick-grid">
        <QuickAction icon={Send} label="Send money" detail="Provider not connected" tone="violet" onClick={onPaymentStatus} />
        <QuickAction icon={QrCode} label="Scan & Pay" detail="Provider not connected" tone="blue" onClick={onPaymentStatus} />
        <QuickAction icon={ArrowDownLeft} label="Receive money" detail="Provider not connected" tone="mint" onClick={onPaymentStatus} />
        <QuickAction icon={ReceiptText} label="Bills & recharges" detail="Provider not connected" tone="peach" onClick={onServices} />
        <QuickAction icon={History} label="Transaction history" detail="Search your activity" tone="peach" onClick={() => navigate("/transactions")} />
        <QuickAction icon={ShieldCheck} label="Security settings" detail="Manage account settings" tone="yellow" onClick={() => navigate("/security")} />
      </div>
    </section>
    <section className="home-capabilities">
      <div className="content-card capability-card">
        <div className="capability-card-heading"><span className="capability-icon"><Banknote size={18} /></span><div><p className="eyebrow">BANK ACCOUNTS</p><h2>No bank linked</h2></div></div>
        <p>Bank balances and transfers are unavailable until a verified banking provider is integrated.</p>
        <button className="text-button" onClick={onBankLinking}>About bank linking <ArrowRight size={15} /></button>
      </div>
      <div className="content-card capability-card">
        <div className="capability-card-heading"><span className="capability-icon rewards-icon"><Sparkles size={18} /></span><div><p className="eyebrow">BILLS & REWARDS</p><h2>Services overview</h2></div></div>
        <p>Explore supported service categories. Payments, due reminders, and rewards are not connected.</p>
        <button className="text-button" onClick={onServices}>View available services <ArrowRight size={15} /></button>
      </div>
    </section>
    <section className="recent-section">
      <div className="section-title-row"><div><p className="eyebrow">ACCOUNT ACTIVITY</p><h2>Transaction history</h2></div><button className="text-button" onClick={onActivity}>Open history <ArrowRight size={15} /></button></div>
      <div className="content-card service-disclosure"><ShieldCheck size={18} /><p>Provider-verified transactions will appear here after a supported payment service is connected. No sample transactions are shown.</p></div>
    </section>
  </>;
}

const serviceCategories = [
  { title: "Mobile recharge", detail: "Prepaid mobile plans", icon: Smartphone },
  { title: "DTH recharge", detail: "Television subscriptions", icon: Tv },
  { title: "Electricity", detail: "Household power bills", icon: Zap },
  { title: "Gas & water", detail: "Utility bill payments", icon: Droplets },
  { title: "Broadband", detail: "Internet subscriptions", icon: Wifi },
  { title: "FASTag", detail: "Toll account recharge", icon: CircleDollarSign },
  { title: "Credit card bill", detail: "Card bill payments", icon: CreditCard },
];

function ServicesPage({ onSelect, onRewards }) {
  return <>
    <PageHeading eyebrow="BILLS, RECHARGES & MORE" title="Bills & services" description="Browse common payment categories. No biller or payment provider is connected." />
    <div className="service-disclosure"><ShieldCheck size={18} /><p><strong>Browse only — payments are unavailable.</strong> SecurePay cannot fetch bills, set due-date reminders, or submit payments. Do not enter account, card, or biller credentials.</p></div>
    <section className="service-section">
      <div className="section-title-row"><div><p className="eyebrow">PAYMENT CATEGORIES</p><h2>Choose a service</h2></div><span className="not-connected-pill">NOT CONNECTED</span></div>
      <div className="service-grid">
        {serviceCategories.map(({ title, detail, icon: Icon }) => <button className="service-tile" key={title} onClick={onSelect}>
          <span className="service-tile-icon"><Icon size={20} /></span><strong>{title}</strong><small>{detail}</small><span className="service-tile-status">Unavailable <ChevronRight size={14} /></span>
        </button>)}
      </div>
    </section>
    <section className="service-bottom-grid">
      <div className="content-card capability-card">
        <div className="capability-card-heading"><span className="capability-icon"><CalendarDays size={18} /></span><div><p className="eyebrow">REMINDERS</p><h2>Due-date reminders</h2></div></div>
        <p>Reminder scheduling is not configured, so this app cannot send bill due-date notifications.</p>
      </div>
      <div className="content-card capability-card">
        <div className="capability-card-heading"><span className="capability-icon rewards-icon"><Sparkles size={18} /></span><div><p className="eyebrow">REWARDS</p><h2>No rewards account</h2></div></div>
        <p>There is no connected loyalty program, points balance, or reward redemption.</p>
        <button className="text-button" onClick={onRewards}>Rewards details <ArrowRight size={15} /></button>
      </div>
    </section>
  </>;
}

function CapabilityModal({ title, eyebrow, children, onClose }) {
  return <Modal title={title} eyebrow={eyebrow} onClose={onClose}>
    <p className="modal-description">{children}</p>
    <div className="capability-modal-note"><ShieldCheck size={16} /><span>No financial information was requested or submitted.</span></div>
    <button className="button button-primary button-full" onClick={onClose}>Got it</button>
  </Modal>;
}

function QuickAction({ icon: Icon, label, detail, tone, onClick }) {
  return <button className="quick-action" onClick={onClick}>
    <span className={`quick-icon tone-${tone}`}><Icon size={20} strokeWidth={1.8} /></span>
    <span className="quick-copy"><strong>{label}</strong><small>{detail}</small></span>
    <ChevronRight className="quick-chevron" size={17} />
  </button>;
}

function TransactionsPage() {
  return <>
    <PageHeading eyebrow="PAYMENT HISTORY" title="Transactions" description="Provider-confirmed account activity." />
    <section className="content-card history-card payment-unavailable-card">
      <span className="receive-icon"><History size={20} /></span>
      <h2>No provider transactions</h2>
      <p>SecurePay does not show sample payment activity. Transactions will appear here after a payment provider is approved and connected.</p>
    </section>
  </>;
}

function ReceivePage() {
  return <>
    <PageHeading eyebrow="PAYMENTS" title="Receive money" description="Incoming payments are not available." />
    <section className="content-card receive-card payment-unavailable-card">
      <span className="receive-icon"><ShieldCheck size={20} /></span>
      <h2>Payment provider not connected</h2>
      <p>SecurePay cannot create a valid bank or UPI QR code or accept funds. Incoming payment features will be unavailable until an approved provider is integrated.</p>
    </section>
  </>;
}

function NotificationsPage({ notifications, onRefresh, onError }) {
  const unread = notifications.filter((item) => item.unread).length;
  const markRead = async (id) => {
    try {
      await apiRequest(`/notifications/${encodeURIComponent(id)}`, { method: "PATCH", body: { read: true } });
      await onRefresh();
    } catch (error) {
      onError(error.message);
    }
  };
  const markAllRead = async () => {
    try {
      await apiRequest("/notifications/read-all", { method: "POST" });
      await onRefresh();
    } catch (error) {
      onError(error.message);
    }
  };
  return <>
    <PageHeading eyebrow="UPDATES & REMINDERS" title="Notifications" description="A little peace of mind, delivered." action={unread > 0 && <button className="text-button" onClick={markAllRead}><Check size={16} /> Mark all read</button>} />
    <section className="content-card notifications-card">
      <div className="notifications-topline"><div><h2>Inbox</h2><p>{unread ? `${unread} unread updates` : "You’re all caught up"}</p></div>      <NavLink className="icon-button" to="/security" aria-label="Open security settings"><Settings2 size={18} /></NavLink></div>
      {notifications.length ? notifications.map((item) => {
        const Icon = item.icon === "shield" ? ShieldCheck : item.icon === "receipt" ? ReceiptText : Sparkles;
        return <article className={`notification-row ${item.unread ? "notification-unread" : ""}`} key={item.id}>
          <span className={`notification-icon ${item.icon}`}><Icon size={18} /></span>
          <div className="notification-copy"><div className="notification-title"><strong>{item.title}</strong>{item.unread && <i />}</div><p>{item.body}</p><small>{item.time}</small></div>
          {item.unread && <button className="mark-read" aria-label={`Mark ${item.title} as read`} onClick={() => markRead(item.id)}><Check size={16} /></button>}
        </article>;
      }) : <div className="empty-state"><div className="empty-icon"><Bell size={22} /></div><strong>No notifications yet</strong><p>Updates will appear here.</p></div>}
    </section>
    <div className="privacy-note"><LockKeyhole size={16} /><span><strong>Privacy</strong> Notifications are stored with your SecurePay profile.</span></div>
  </>;
}

function ProfilePage({ profile, setProfile, onToast }) {
  const [form, setForm] = useState(profile);
  const [editing, setEditing] = useState(false);
  const [profileError, setProfileError] = useState("");
  const update = (event) => {
    setProfileError("");
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };
  const save = async (event) => {
    event.preventDefault();
    if (!form.name.trim() || !/^[a-z0-9._-]{3,30}$/i.test(form.handle.trim())) {
      setProfileError("Enter a display name and a 3–30 character profile ID using letters, numbers, dots, underscores, or hyphens.");
      return;
    }
    try {
      const updated = await apiRequest("/profile", {
        method: "PATCH",
        body: { display_name: form.name.trim(), demo_handle: form.handle.trim().toLowerCase() },
      });
      const nextProfile = toProfile(updated);
      setProfile(nextProfile);
      setForm(nextProfile);
      setEditing(false);
      onToast("Your profile has been updated.");
    } catch (error) {
      setProfileError(error.message);
    }
  };
  return <>
    <PageHeading eyebrow="ACCOUNT" title="Profile" description="Manage your SecurePay profile." action={<button className="button button-outline" onClick={() => { setForm(profile); setEditing((current) => !current); }}>{editing ? <X size={16} /> : <Settings2 size={16} />}{editing ? "Cancel" : "Edit profile"}</button>} />
    <div className="profile-layout">
      <section className="content-card profile-card">
        <div className="profile-cover"><div className="cover-orb cover-orb-a" /><div className="cover-orb cover-orb-b" /><span className="demo-pill">SECUREPAY ACCOUNT</span></div>
        <div className="profile-identity"><Avatar name={profile.name} color="peach" size="large" /><div><h2>{profile.name}</h2><p>@{profile.handle}</p></div><span className="verified-badge"><BadgeCheck size={15} /> SecurePay profile</span></div>
        <div className="profile-divider" />
        {editing ? <form className="profile-form" onSubmit={save}>
          <label className="field-label">Display name<input name="name" maxLength="60" required value={form.name} onChange={update} /></label>
          <label className="field-label">Profile ID<input name="handle" minLength="3" maxLength="30" required value={form.handle} onChange={update} /><small>Phone verification and bank details are not supported.</small></label>
          {profileError && <p className="form-error profile-error" role="alert">{profileError}</p>}
          <button className="button button-primary" type="submit"><Check size={16} /> Save changes</button>
        </form> : <div className="profile-details">
          <ProfileDetail icon={UserRound} label="Display name" value={profile.name} />
          <ProfileDetail icon={KeyRound} label="Profile ID" value={`@${profile.handle}`} />
            <ProfileDetail icon={Wallet} label="Account type" value="SecurePay profile" />
            <ProfileDetail icon={ShieldCheck} label="Profile status" value="Unverified profile" />
        </div>}
      </section>
      <aside className="profile-aside">
        <div className="content-card membership-card"><span className="membership-icon"><Gift size={19} /></span><p className="eyebrow">YOUR SECUREPAY JOURNEY</p><h3>Curious looks good on you.</h3><p>You’ve been exploring SecurePay since November 2025.</p><div className="member-since"><Sparkles size={15} /> Member since Nov ’25</div></div>
        <div className="content-card profile-safety"><ShieldCheck size={18} /><div><strong>Payment services offline</strong><p>This profile is not connected to a bank or payment network.</p></div></div>
      </aside>
    </div>
  </>;
}

function ProfileDetail({ icon: Icon, label, value }) {
  return <div className="profile-detail"><span className="detail-icon"><Icon size={17} /></span><span><small>{label}</small><strong>{value}</strong></span><span className="detail-edit-label">INFO</span></div>;
}

function SecurityPage({ preferences, sessions, setPreferences, setSessions, onChangePassword, onToast }) {
  const savePreference = async (key) => {
    const next = { ...preferences, [key]: !preferences[key] };
    setPreferences(next);
    try {
      await apiRequest("/preferences", { method: "PUT", body: next });
    } catch (error) {
      setPreferences(preferences);
      onToast(error.message);
    }
  };
  const revokeSession = async (session) => {
    try {
      await apiRequest(`/auth/sessions/${encodeURIComponent(session.id)}`, { method: "DELETE" });
      setSessions((current) => current.filter((entry) => entry.id !== session.id));
      onToast("Session revoked.");
    } catch (error) {
      onToast(error.message);
    }
  };
  return <>
    <PageHeading eyebrow="ACCOUNT PROTECTION" title="Security" description="Security controls and service status." />
    <div className="security-layout">
      <section className="content-card security-card">
        <div className="security-section-head"><div><p className="eyebrow">SIGN-IN & SAFETY</p><h2>Security preferences</h2></div><span className="security-score"><ShieldCheck size={15} /> Account controls</span></div>
        <SecuritySetting icon={Fingerprint} title="Biometric sign-in" description="A visual preference only — no biometric data is collected." enabled={preferences.biometric_preference} onToggle={() => savePreference("biometric_preference")} />
        <SecuritySetting icon={Bell} title="Security alerts" description="Show account security and blocked-attempt alerts in the app." enabled={preferences.security_alerts} onToggle={() => savePreference("security_alerts")} />
        <button className="security-row-action" onClick={onChangePassword}><span className="setting-icon"><KeyRound size={18} /></span><span><strong>Password security</strong><small>Change your password and sign out other sessions.</small></span><ArrowRight size={16} /></button>
        <div className="security-row-action security-static-row"><span className="setting-icon"><Smartphone size={18} /></span><span><strong>Verified mobile number</strong><small>No phone number is verified; SMS/OTP delivery is not configured.</small></span><span className="coming-soon">UNAVAILABLE</span></div>
        <div className="security-row-action security-static-row"><span className="setting-icon"><Shield size={18} /></span><span><strong>Payment approval</strong><small>Unavailable until an approved payment provider is connected.</small></span><span className="coming-soon">UNAVAILABLE</span></div>
      </section>
      <section className="content-card sessions-card">
        <div className="sessions-heading"><div><p className="eyebrow">DEVICES & SESSIONS</p><h2>Active sessions</h2></div><span className="session-count">{sessions.length}</span></div>
        <p className="sessions-description">Review and revoke browser sessions. This is session management, not cryptographic device binding.</p>
        {sessions.map((session) => <div className="session-row" key={session.id}>
          <span className="session-device"><Settings2 size={18} /></span>
          <span className="session-copy"><strong>{session.label || "SecurePay session"} {session.current && <i className="current-badge">THIS DEVICE</i>}</strong><small>{session.current ? "This device · Active now" : `Signed in ${new Date(session.created_at).toLocaleString()}`}</small></span>
          {!session.current && <button className="revoke-button" onClick={() => revokeSession(session)}>Revoke</button>}
        </div>)}
        {!sessions.some((session) => !session.current) && <div className="empty-sessions"><CheckCircle2 size={19} /> No other active sessions</div>}
        <div className="session-footnote"><LockKeyhole size={14} /> Signing out or revoking a session invalidates its server-side token.</div>
      </section>
    </div>
    <div className="security-callout"><span><ShieldCheck size={19} /></span><div><strong>Security, without the sensitive stuff.</strong><p>SecurePay never asks for real banking passwords, UPI PINs, OTPs, card details, or government ID numbers.</p></div></div>
    <section className="content-card security-readiness">
      <p className="eyebrow">DEPLOYMENT & OPERATIONS</p>
      <h2>Controls that still need production services</h2>
      <ul>
        <li><strong>Recovery:</strong> unavailable until a verified contact channel and secure recovery provider are configured.</li>
        <li><strong>Transport and storage:</strong> production startup requires secure session cookies and PostgreSQL TLS verification; encrypted database storage and backups must be enabled by the hosting provider.</li>
        <li><strong>Monitoring:</strong> suspicious attempts are written to audit records and application security logs; no external alerting, incident-response service, or on-call procedure is connected.</li>
        <li><strong>Device binding:</strong> cryptographic binding is not configured. Revoke sessions here and use a strong unique password.</li>
      </ul>
    </section>
  </>;
}

function SecuritySetting({ icon: Icon, title, description, enabled, onToggle }) {
  return <div className="security-setting"><span className="setting-icon"><Icon size={18} /></span><span className="setting-copy"><strong>{title}</strong><small>{description}</small></span><button className={`toggle ${enabled ? "toggle-on" : ""}`} role="switch" aria-checked={enabled} aria-label={title} onClick={onToggle}><span /></button></div>;
}

function PasswordModal({ onClose, onComplete }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const response = await apiRequest("/auth/password", {
        method: "PUT",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      onComplete(response);
    } catch (requestError) {
      setError(requestError.message || "Unable to change the password.");
    } finally {
      setBusy(false);
    }
  };
  return <Modal title="Change password" eyebrow="ACCOUNT SECURITY" onClose={onClose}>
    <form className="send-form" onSubmit={submit}>
      <p className="modal-description">Choose a new password. Other active sessions will be signed out.</p>
      <label className="field-label">Current password<input type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
      <label className="field-label">New password<input type="password" autoComplete="new-password" minLength="12" maxLength="128" required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /><small>Use at least 12 characters.</small></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button button-primary button-full" disabled={busy} type="submit">{busy ? "Updating…" : "Update password"} <ArrowRight size={16} /></button>
    </form>
  </Modal>;
}

function HelpModal({ onClose, onNavigate }) {
  return <Modal title="SecurePay information" eyebrow="SERVICE STATUS" onClose={onClose}>
    <p className="modal-description">SecurePay is not connected to banks, UPI, billers, or payment networks. No bank balance or payment history is available, and payment actions are disabled until an approved provider is integrated.</p>
    <div className="help-links">
      <button className="security-row-action" onClick={() => onNavigate("/transactions")}><span className="setting-icon"><History size={18} /></span><span><strong>Find a transaction</strong><small>Search, filter, or open a receipt.</small></span><ChevronRight size={18} /></button>
      <button className="security-row-action" onClick={() => onNavigate("/security")}><span className="setting-icon"><ShieldCheck size={18} /></span><span><strong>Review security</strong><small>Explore privacy notes and security preferences.</small></span><ChevronRight size={18} /></button>
    </div>
    <p className="demo-inline-note"><LockKeyhole size={14} /> Never enter real passwords, PINs, OTPs, or bank details.</p>
  </Modal>;
}

export default App;
