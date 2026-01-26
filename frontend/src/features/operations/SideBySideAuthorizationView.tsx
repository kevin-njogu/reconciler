import { useState, useMemo } from 'react';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  User,
  MessageSquare,
} from 'lucide-react';
import type { UnreconciledTransaction } from '@/api/operations';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableEmpty,
  Badge,
  Button,
} from '@/components/ui';
import { formatDateTime, formatCurrency, cn } from '@/lib/utils';

interface AuthorizationPanelProps {
  title: string;
  transactions: UnreconciledTransaction[];
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAll: () => void;
  onAuthorize: (txn: UnreconciledTransaction) => void;
  onReject: (txn: UnreconciledTransaction) => void;
  variant: 'internal' | 'external';
}

type SortField = 'date' | 'transaction_id' | 'amount' | 'reconciled_by';
type SortDirection = 'asc' | 'desc';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

function AuthorizationPanel({
  title,
  transactions,
  selectedIds,
  onToggleSelection,
  onToggleAll,
  onAuthorize,
  onReject,
  variant,
}: AuthorizationPanelProps) {
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Calculate summary
  const summary = useMemo(() => {
    let totalDebit = 0;
    let totalCredit = 0;
    transactions.forEach((txn) => {
      if (txn.debit) totalDebit += txn.debit;
      if (txn.credit) totalCredit += txn.credit;
    });
    return {
      count: transactions.length,
      totalDebit,
      totalCredit,
      totalAmount: totalDebit + totalCredit,
    };
  }, [transactions]);

  // Sort transactions
  const sortedTransactions = useMemo(() => {
    const sorted = [...transactions].sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'date':
          comparison = (a.manual_recon_at || '').localeCompare(b.manual_recon_at || '');
          break;
        case 'transaction_id':
          comparison = (a.transaction_id || '').localeCompare(b.transaction_id || '');
          break;
        case 'reconciled_by':
          comparison = (a.manual_recon_by_username || '').localeCompare(
            b.manual_recon_by_username || ''
          );
          break;
        case 'amount': {
          const amountA = a.debit || a.credit || a.amount || 0;
          const amountB = b.debit || b.credit || b.amount || 0;
          comparison = amountA - amountB;
          break;
        }
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return sorted;
  }, [transactions, sortField, sortDirection]);

  // Paginate transactions
  const totalPages = Math.ceil(sortedTransactions.length / pageSize);
  const paginatedTransactions = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedTransactions.slice(start, start + pageSize);
  }, [sortedTransactions, currentPage, pageSize]);

  // Reset to page 1 when pageSize changes
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(1);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-3 w-3 ml-1" />
    ) : (
      <ArrowDown className="h-3 w-3 ml-1" />
    );
  };

  const allSelected =
    paginatedTransactions.length > 0 &&
    paginatedTransactions.every((t) => selectedIds.has(t.id));
  const someSelected = paginatedTransactions.some((t) => selectedIds.has(t.id));

  const bgColor = variant === 'internal' ? 'bg-blue-50' : 'bg-amber-50';
  const borderColor = variant === 'internal' ? 'border-blue-200' : 'border-amber-200';
  const headerBg = variant === 'internal' ? 'bg-blue-100' : 'bg-amber-100';

  return (
    <Card className={cn('flex flex-col h-full', borderColor, 'border-2')}>
      <CardHeader className={cn(headerBg, 'py-3')}>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>{title}</span>
          <Badge variant={variant === 'internal' ? 'info' : 'warning'}>
            {summary.count} pending
          </Badge>
        </CardTitle>
      </CardHeader>

      {/* Summary Stats */}
      <div className={cn('grid grid-cols-3 gap-2 p-3 border-b', bgColor)}>
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase">Count</p>
          <p className="text-lg font-semibold">{summary.count}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase">Total Debit</p>
          <p className="text-lg font-semibold text-red-600">{formatCurrency(summary.totalDebit)}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase">Total Credit</p>
          <p className="text-lg font-semibold text-green-600">
            {formatCurrency(summary.totalCredit)}
          </p>
        </div>
      </div>

      <CardContent className="p-0 flex-1 overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10 sticky top-0 bg-neutral-50">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected && !allSelected;
                  }}
                  onChange={onToggleAll}
                  className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-400"
                />
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 sticky top-0 bg-neutral-50"
                onClick={() => handleSort('transaction_id')}
              >
                <div className="flex items-center">
                  Transaction <SortIcon field="transaction_id" />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 sticky top-0 bg-neutral-50"
                onClick={() => handleSort('reconciled_by')}
              >
                <div className="flex items-center">
                  Reconciled By <SortIcon field="reconciled_by" />
                </div>
              </TableHead>
              <TableHead className="sticky top-0 bg-neutral-50">Note</TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 text-right sticky top-0 bg-neutral-50"
                onClick={() => handleSort('amount')}
              >
                <div className="flex items-center justify-end">
                  Amount <SortIcon field="amount" />
                </div>
              </TableHead>
              <TableHead className="w-32 sticky top-0 bg-neutral-50">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedTransactions.length === 0 ? (
              <TableEmpty message="No pending authorizations" colSpan={6} />
            ) : (
              paginatedTransactions.map((txn) => (
                <TableRow key={txn.id}>
                  <TableCell className="py-2">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(txn.id)}
                      onChange={() => onToggleSelection(txn.id)}
                      className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-400"
                    />
                  </TableCell>
                  <TableCell className="py-2">
                    <div className="space-y-1">
                      <div className="font-mono text-xs">{txn.transaction_id || '-'}</div>
                      <div
                        className="text-xs text-neutral-500 max-w-[120px] truncate"
                        title={txn.narrative || ''}
                      >
                        {txn.narrative || '-'}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="py-2">
                    <div className="flex items-center gap-1">
                      <User className="h-3 w-3 text-neutral-400" />
                      <div>
                        <div className="text-xs">{txn.manual_recon_by_username || 'Unknown'}</div>
                        <div className="text-xs text-neutral-500">
                          {txn.manual_recon_at ? formatDateTime(txn.manual_recon_at) : '-'}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="py-2">
                    <div
                      className="flex items-start gap-1 max-w-[100px]"
                      title={txn.manual_recon_note || ''}
                    >
                      <MessageSquare className="h-3 w-3 text-neutral-400 mt-0.5 flex-shrink-0" />
                      <span className="text-xs text-neutral-600 line-clamp-2">
                        {txn.manual_recon_note || '-'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="py-2 text-right font-mono text-xs">
                    {txn.debit ? (
                      <span className="text-red-600">{formatCurrency(txn.debit)}</span>
                    ) : txn.credit ? (
                      <span className="text-green-600">{formatCurrency(txn.credit)}</span>
                    ) : txn.amount ? (
                      formatCurrency(txn.amount)
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell className="py-2">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => onAuthorize(txn)}
                        className="text-xs px-2 py-1"
                      >
                        <CheckCircle className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => onReject(txn)}
                        className="text-xs px-2 py-1"
                      >
                        <XCircle className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>

      {/* Pagination Controls */}
      {sortedTransactions.length > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary-400"
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">
              {(currentPage - 1) * pageSize + 1}-
              {Math.min(currentPage * pageSize, sortedTransactions.length)} of{' '}
              {sortedTransactions.length}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-1 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}

interface SideBySideAuthorizationViewProps {
  groups: Array<{
    batch_id: string;
    gateway: string;
    transactions: UnreconciledTransaction[];
  }>;
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAllInternal: (transactions: UnreconciledTransaction[]) => void;
  onToggleAllExternal: (transactions: UnreconciledTransaction[]) => void;
  onAuthorize: (txn: UnreconciledTransaction) => void;
  onReject: (txn: UnreconciledTransaction) => void;
}

export function SideBySideAuthorizationView({
  groups,
  selectedIds,
  onToggleSelection,
  onToggleAllInternal,
  onToggleAllExternal,
  onAuthorize,
  onReject,
}: SideBySideAuthorizationViewProps) {
  // Separate internal (workpay_*) and external transactions
  const { internalTransactions, externalTransactions, internalGateways, externalGateways } =
    useMemo(() => {
      const internal: UnreconciledTransaction[] = [];
      const external: UnreconciledTransaction[] = [];
      const intGateways: string[] = [];
      const extGateways: string[] = [];

      groups.forEach((group) => {
        if (group.gateway.toLowerCase().startsWith('workpay_')) {
          internal.push(...group.transactions);
          if (!intGateways.includes(group.gateway)) intGateways.push(group.gateway);
        } else {
          external.push(...group.transactions);
          if (!extGateways.includes(group.gateway)) extGateways.push(group.gateway);
        }
      });

      return {
        internalTransactions: internal,
        externalTransactions: external,
        internalGateways: intGateways,
        externalGateways: extGateways,
      };
    }, [groups]);

  const internalTitle =
    internalGateways.length > 0
      ? `Internal (${internalGateways.map((g) => g.replace('workpay_', '')).join(', ')})`
      : 'Internal (Workpay)';

  const externalTitle =
    externalGateways.length > 0
      ? `External (${externalGateways.join(', ')})`
      : 'External (Bank)';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100vh-300px)] min-h-[500px]">
      <AuthorizationPanel
        title={externalTitle}
        transactions={externalTransactions}
        selectedIds={selectedIds}
        onToggleSelection={onToggleSelection}
        onToggleAll={() => onToggleAllExternal(externalTransactions)}
        onAuthorize={onAuthorize}
        onReject={onReject}
        variant="external"
      />
      <AuthorizationPanel
        title={internalTitle}
        transactions={internalTransactions}
        selectedIds={selectedIds}
        onToggleSelection={onToggleSelection}
        onToggleAll={() => onToggleAllInternal(internalTransactions)}
        onAuthorize={onAuthorize}
        onReject={onReject}
        variant="internal"
      />
    </div>
  );
}
