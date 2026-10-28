import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowDownLeft,
  ArrowUpDown,
  ArrowUpRight,
  Calendar,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  Eye,
  FileSpreadsheet,
  Filter,
  History,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  XCircle,
} from "lucide-react";
import { api } from "../api.js";

export default function TransactionLedger({ onSelectTransaction }) {
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState({
    total_credits_paise: 0,
    total_debits_paise: 0,
    pending_count: 0,
    successful_count: 0,
    failed_count: 0,
  });
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters state
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState("all");
  const [period, setPeriod] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sort, setSort] = useState("date_desc");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const loadLedger = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getTransactions({
        search,
        direction,
        period,
        status: statusFilter,
        sort,
        page,
        page_size: pageSize,
        paginated: true,
      });

      if (data && data.transactions) {
        setTransactions(data.transactions);
        setTotal(data.total || 0);
        setTotalPages(data.total_pages || 1);
        if (data.summary) {
          setSummary(data.summary);
        }
      } else if (Array.isArray(data)) {
        setTransactions(data);
        setTotal(data.length);
        setTotalPages(1);
      }
    } catch (err) {
      setError(err.message || "Failed to load ledger transactions.");
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [search, direction, period, statusFilter, sort, page]);

  useEffect(() => {
    loadLedger();
  }, [loadLedger]);

  const handleExportCSV = () => {
    const exportUrl = api.getTransactionsExportUrl({
      search,
      direction,
      period,
    });
    window.location.href = exportUrl;
  };

  const handleResetFilters = () => {
    setSearch("");
    setDirection("all");
    setPeriod("all");
    setStatusFilter("all");
    setSort("date_desc");
    setPage(1);
  };

  const getStatusBadge = (tx) => {
    const s = (tx.status || "Completed").toLowerCase();
    if (s.includes("success") || s.includes("completed") || s.includes("paid") || s.includes("posted")) {
      return <span className="tx-status-pill successful">SUCCESSFUL</span>;
    }
    if (s.includes("pending")) {
      return <span className="tx-status-pill pending">PENDING</span>;
    }
    if (s.includes("process")) {
      return <span className="tx-status-pill processing">PROCESSING</span>;
    }
    if (s.includes("init")) {
      return <span className="tx-status-pill initiated">INITIATED</span>;
    }
    if (s.includes("fail")) {
      return <span className="tx-status-pill failed">FAILED</span>;
    }
    if (s.includes("revers")) {
      return <span className="tx-status-pill reversed">REVERSED</span>;
    }
    if (s.includes("refund")) {
      return <span className="tx-status-pill refunded">REFUNDED</span>;
    }
    return <span className="tx-status-pill completed">{tx.status?.toUpperCase() || "POSTED"}</span>;
  };

  return (
    <div className="ledger-page animate-fade-in">
      {/* Page Heading & Actions */}
      <div className="page-heading d-flex justify-between align-center">
        <div>
          <h1 className="page-title">Transaction Ledger</h1>
          <p className="page-subtitle">
            Fintech-grade double-entry settlement ledger with audit verification & export
          </p>
        </div>
        <div className="ledger-actions-group">
          <button className="secondary-action-btn" onClick={handleExportCSV} title="Export CSV">
            <FileSpreadsheet size={16} />
            <span>Export CSV</span>
          </button>
          <button className="secondary-action-btn" onClick={loadLedger} title="Refresh Ledger">
            <RefreshCw size={15} className={loading ? "spin-icon" : ""} />
            <span className="d-none d-sm-inline">Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-error mb-4">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Summary Cards (Total Credits, Debits, Pending, Successful, Failed) */}
      <div className="ledger-summary-grid mb-4">
        <div className="ledger-summary-card credit">
          <div className="summary-icon-circle">
            <ArrowDownLeft size={20} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-title">TOTAL CREDITS</span>
            <h3 className="summary-card-value text-teal">
              ₹{((summary.total_credits_paise || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </h3>
            <span className="summary-card-meta">Settled inflows</span>
          </div>
        </div>

        <div className="ledger-summary-card debit">
          <div className="summary-icon-circle">
            <ArrowUpRight size={20} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-title">TOTAL DEBITS</span>
            <h3 className="summary-card-value text-coral">
              ₹{((summary.total_debits_paise || 0) / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </h3>
            <span className="summary-card-meta">Settled outflows</span>
          </div>
        </div>

        <div className="ledger-summary-card success">
          <div className="summary-icon-circle">
            <CheckCircle2 size={20} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-title">SUCCESSFUL</span>
            <h3 className="summary-card-value">{summary.successful_count || 0}</h3>
            <span className="summary-card-meta">Confirmed transactions</span>
          </div>
        </div>

        <div className="ledger-summary-card pending">
          <div className="summary-icon-circle">
            <Clock size={20} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-title">PENDING</span>
            <h3 className="summary-card-value text-amber">{summary.pending_count || 0}</h3>
            <span className="summary-card-meta">Awaiting reconciliation</span>
          </div>
        </div>

        <div className="ledger-summary-card failed">
          <div className="summary-icon-circle">
            <XCircle size={20} />
          </div>
          <div className="summary-card-body">
            <span className="summary-card-title">FAILED</span>
            <h3 className="summary-card-value">{summary.failed_count || 0}</h3>
            <span className="summary-card-meta">Rejected / reversed</span>
          </div>
        </div>
      </div>

      {/* 2. Search & Multi-Faceted Filter Toolbar */}
      <div className="content-card filter-toolbar-card mb-4">
        {/* Search row */}
        <div className="search-input-wrap mb-3">
          <Search size={18} className="search-icon text-muted" />
          <input
            type="text"
            className="filter-search-input"
            placeholder="Search by transaction reference, counterparty name, handle, or note..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          {search && (
            <button className="clear-search-btn" onClick={() => setSearch("")}>
              ✕
            </button>
          )}
        </div>

        {/* Filter controls row */}
        <div className="filter-controls-row">
          {/* Direction */}
          <div className="filter-group">
            <span className="filter-label">Flow:</span>
            {["all", "received", "sent"].map((d) => (
              <button
                key={d}
                type="button"
                className={`filter-chip ${direction === d ? "active" : ""}`}
                onClick={() => {
                  setDirection(d);
                  setPage(1);
                }}
              >
                {d === "all" ? "ALL" : d === "received" ? "CREDIT" : "DEBIT"}
              </button>
            ))}
          </div>

          {/* Period */}
          <div className="filter-group">
            <span className="filter-label">Period:</span>
            {[
              { id: "all", label: "ALL TIME" },
              { id: "week", label: "7 DAYS" },
              { id: "month", label: "THIS MONTH" },
              { id: "year", label: "THIS YEAR" },
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                className={`filter-chip ${period === p.id ? "active" : ""}`}
                onClick={() => {
                  setPeriod(p.id);
                  setPage(1);
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Sort Dropdown */}
          <div className="filter-group ml-auto">
            <span className="filter-label">Sort:</span>
            <select
              className="filter-select-input"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              <option value="date_desc">Newest First</option>
              <option value="date_asc">Oldest First</option>
              <option value="amount_desc">Highest Amount</option>
              <option value="amount_asc">Lowest Amount</option>
            </select>
          </div>
        </div>
      </div>

      {/* 3. Clean Transaction Table & Mobile Cards */}
      <div className="content-card ledger-table-card">
        {loading ? (
          <div className="skeleton-loading-wrap p-4">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        ) : transactions.length > 0 ? (
          <>
            {/* Desktop / Tablet Table */}
            <div className="table-responsive d-none d-md-block">
              <table className="ledger-table">
                <thead>
                  <tr>
                    <th>REFERENCE & ID</th>
                    <th>DATE & TIME</th>
                    <th>COUNTERPARTY</th>
                    <th>CATEGORY & METHOD</th>
                    <th className="text-right">AMOUNT</th>
                    <th>STATUS</th>
                    <th className="text-center">ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => {
                    const isCredit = tx.signed_amount_paise > 0;
                    return (
                      <tr
                        key={tx.reference}
                        className="ledger-row"
                        onClick={() => onSelectTransaction(tx)}
                      >
                        <td>
                          <div className="ref-cell">
                            <strong className="font-mono text-teal">{tx.reference}</strong>
                            {tx.id && (
                              <small className="font-mono text-muted d-block">{tx.id.slice(0, 8)}...</small>
                            )}
                          </div>
                        </td>

                        <td>
                          <div className="date-cell">
                            <span>{new Date(tx.created_at).toLocaleDateString()}</span>
                            <small className="text-muted d-block">
                              {new Date(tx.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </small>
                          </div>
                        </td>

                        <td>
                          <div className="counterparty-cell">
                            <strong>{tx.name}</strong>
                            {tx.handle && (
                              <small className="text-muted font-mono d-block">@{tx.handle}</small>
                            )}
                          </div>
                        </td>

                        <td>
                          <div className="category-cell">
                            <span>{tx.category}</span>
                            <small className="text-muted d-block">{tx.method || "SecurePay UPI"}</small>
                          </div>
                        </td>

                        <td className="text-right">
                          <span className={`ledger-amount-pill ${isCredit ? "credit" : "debit"}`}>
                            {isCredit ? "+" : "-"}₹{(Math.abs(tx.amount_paise) / 100).toFixed(2)}
                          </span>
                        </td>

                        <td>{getStatusBadge(tx)}</td>

                        <td className="text-center" onClick={(e) => e.stopPropagation()}>
                          <button
                            className="view-detail-btn"
                            onClick={() => onSelectTransaction(tx)}
                            title="View Transaction Details"
                          >
                            <Eye size={15} />
                            <span>Details</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards View (< 768px) */}
            <div className="mobile-ledger-cards d-md-none">
              {transactions.map((tx) => {
                const isCredit = tx.signed_amount_paise > 0;
                return (
                  <div
                    key={tx.reference}
                    className="mobile-tx-card"
                    onClick={() => onSelectTransaction(tx)}
                  >
                    <div className="card-top-row">
                      <div className="d-flex align-center">
                        <div className={`tx-icon-circle small ${isCredit ? "credit" : "debit"}`}>
                          {isCredit ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
                        </div>
                        <div className="ml-2">
                          <strong className="tx-name">{tx.name}</strong>
                          <small className="font-mono text-muted d-block">{tx.reference}</small>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`tx-amount ${isCredit ? "credit" : "debit"}`}>
                          {isCredit ? "+" : "-"}₹{(Math.abs(tx.amount_paise) / 100).toFixed(2)}
                        </span>
                        <div className="mt-1">{getStatusBadge(tx)}</div>
                      </div>
                    </div>

                    <div className="card-bottom-row mt-2 pt-2 border-top d-flex justify-between text-muted text-sm">
                      <span>{tx.category}</span>
                      <span>{new Date(tx.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 4. Pagination Controls */}
            <div className="ledger-pagination-bar mt-3 pt-3 border-top d-flex justify-between align-center">
              <span className="text-muted text-sm">
                Showing {transactions.length} of {total} records • Page {page} of {totalPages}
              </span>

              <div className="pagination-buttons-group">
                <button
                  className="pagination-btn"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft size={16} />
                  <span>Prev</span>
                </button>

                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pNum = i + 1;
                  return (
                    <button
                      key={pNum}
                      className={`pagination-btn ${page === pNum ? "active" : ""}`}
                      onClick={() => setPage(pNum)}
                    >
                      {pNum}
                    </button>
                  );
                })}

                <button
                  className="pagination-btn"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                >
                  <span>Next</span>
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="empty-state-box py-5 text-center">
            <History size={44} className="text-muted mx-auto mb-2" />
            <h4>No transactions match your criteria</h4>
            <p className="text-muted">
              {search || direction !== "all" || period !== "all"
                ? "Try adjusting your search keywords, direction, or time range."
                : "No transactions recorded in the ledger yet."}
            </p>
            {(search || direction !== "all" || period !== "all") && (
              <button className="secondary-action-btn mt-3 mx-auto" onClick={handleResetFilters}>
                Reset All Filters
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

