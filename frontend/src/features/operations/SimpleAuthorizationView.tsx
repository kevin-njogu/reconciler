import { useState, useMemo } from 'react';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
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

interface SimpleAuthorizationPanelProps {
  title: string;
  transactions: UnreconciledTransaction[];
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAll: () => void;
  onAuthorize: (txn: UnreconciledTransaction) => void;
  onReject: (txn: UnreconciledTransaction) => void;
  variant: 'internal' | 'external';
}

type SortField = 'date' | 'reference' | 'amount';
type SortDirection = 'asc' | 'desc';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

function SimpleAuthorizationPanel({
  title,
  transactions,
  selectedIds,
  onToggleSelection,
  onToggleAll,
  onAuthorize,
  onReject,
  variant,
}: SimpleAuthorizationPanelProps) {
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Calculate summary
  const summary = useMemo(() => {
    let totalAmount = 0;
    transactions.forEach((txn) => {
      const amount = txn.debit || txn.credit || txn.amount || 0;
      totalAmount += amount;
    });
    return {
      count: transactions.length,
      totalAmount,
    };
  }, [transactions]);

  // Sort transactions
  const sortedTransactions = useMemo(() => {
    const sorted = [...transactions].sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'date':
          comparison = (a.date || '').localeCompare(b.date || '');
          break;
        case 'reference':
          comparison = (a.transaction_id || '').localeCompare(b.transaction_id || '');
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
      <div className={cn('grid grid-cols-2 gap-2 p-3 border-b', bgColor)}>
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase">Count</p>
          <p className="text-lg font-semibold">{summary.count}</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-500 uppercase">Total Amount</p>
          <p className="text-lg font-semibold">{formatCurrency(summary.totalAmount)}</p>
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
                onClick={() => handleSort('date')}
              >
                <div className="flex items-center">
                  Date <SortIcon field="date" />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 sticky top-0 bg-neutral-50"
                onClick={() => handleSort('reference')}
              >
                <div className="flex items-center">
                  Reference <SortIcon field="reference" />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 text-right sticky top-0 bg-neutral-50"
                onClick={() => handleSort('amount')}
              >
                <div className="flex items-center justify-end">
                  Amount <SortIcon field="amount" />
                </div>
              </TableHead>
              <TableHead className="w-24 sticky top-0 bg-neutral-50">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedTransactions.length === 0 ? (
              <TableEmpty message="No pending authorizations" colSpan={5} />
            ) : (
              paginatedTransactions.map((txn) => {
                const amount = txn.debit || txn.credit || txn.amount || 0;
                return (
                  <TableRow key={txn.id}>
                    <TableCell className="py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(txn.id)}
                        onChange={() => onToggleSelection(txn.id)}
                        className="h-4 w-4 rounded border-gray-300 text-primary-500 focus:ring-primary-400"
                      />
                    </TableCell>
                    <TableCell className="py-2 text-sm text-gray-600 whitespace-nowrap">
                      {txn.date ? formatDateTime(txn.date) : '-'}
                    </TableCell>
                    <TableCell className="py-2 font-mono text-sm" title={txn.transaction_id || ''}>
                      {txn.transaction_id || '-'}
                    </TableCell>
                    <TableCell className="py-2 text-right font-mono text-sm whitespace-nowrap">
                      {formatCurrency(amount)}
                    </TableCell>
                    <TableCell className="py-2">
                      <div className="flex items-center gap-1">
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => onAuthorize(txn)}
                          className="text-xs px-2 py-1"
                          title="Authorize"
                        >
                          <CheckCircle className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => onReject(txn)}
                          className="text-xs px-2 py-1"
                          title="Reject"
                        >
                          <XCircle className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </CardContent>

      {/* Pagination Controls */}
      {sortedTransactions.length > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Rows:</span>
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

interface SimpleAuthorizationViewProps {
  groups: Array<{
    gateway: string;
    transactions: UnreconciledTransaction[];
  }>;
  selectedGateway: string;
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAllInternal: (transactions: UnreconciledTransaction[]) => void;
  onToggleAllExternal: (transactions: UnreconciledTransaction[]) => void;
  onAuthorize: (txn: UnreconciledTransaction) => void;
  onReject: (txn: UnreconciledTransaction) => void;
}

export function SimpleAuthorizationView({
  groups,
  selectedGateway,
  selectedIds,
  onToggleSelection,
  onToggleAllInternal,
  onToggleAllExternal,
  onAuthorize,
  onReject,
}: SimpleAuthorizationViewProps) {
  // Filter and separate transactions for the selected base gateway
  const { internalTransactions, externalTransactions } = useMemo(() => {
    const internal: UnreconciledTransaction[] = [];
    const external: UnreconciledTransaction[] = [];

    groups.forEach((group) => {
      const gatewayLower = group.gateway.toLowerCase();
      const baseGateway = gatewayLower.replace(/_internal$/, '').replace(/_external$/, '');

      // Only include transactions for the selected gateway
      if (baseGateway !== selectedGateway.toLowerCase()) {
        return;
      }

      if (gatewayLower.endsWith('_internal')) {
        internal.push(...group.transactions);
      } else if (gatewayLower.endsWith('_external')) {
        external.push(...group.transactions);
      } else {
        // Fallback: if no suffix, treat as external
        external.push(...group.transactions);
      }
    });

    return {
      internalTransactions: internal,
      externalTransactions: external,
    };
  }, [groups, selectedGateway]);

  const displayGateway = selectedGateway.charAt(0).toUpperCase() + selectedGateway.slice(1);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[500px]">
      <SimpleAuthorizationPanel
        title={`External (${displayGateway})`}
        transactions={externalTransactions}
        selectedIds={selectedIds}
        onToggleSelection={onToggleSelection}
        onToggleAll={() => onToggleAllExternal(externalTransactions)}
        onAuthorize={onAuthorize}
        onReject={onReject}
        variant="external"
      />
      <SimpleAuthorizationPanel
        title={`Internal (Workpay ${displayGateway})`}
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
