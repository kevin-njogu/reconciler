import { useState, useMemo } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight } from 'lucide-react';
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

interface TransactionPanelProps {
  title: string;
  transactions: UnreconciledTransaction[];
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAll: () => void;
  onReconcileClick: (txn: UnreconciledTransaction) => void;
  variant: 'internal' | 'external';
}

type SortField = 'date' | 'narrative' | 'reconciliation_key' | 'amount';
type SortDirection = 'asc' | 'desc';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

function TransactionPanel({
  title,
  transactions,
  selectedIds,
  onToggleSelection,
  onToggleAll,
  onReconcileClick,
  variant,
}: TransactionPanelProps) {
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
          comparison = (a.date || '').localeCompare(b.date || '');
          break;
        case 'narrative':
          comparison = (a.narrative || '').localeCompare(b.narrative || '');
          break;
        case 'reconciliation_key':
          comparison = (a.reconciliation_key || '').localeCompare(b.reconciliation_key || '');
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

  const allSelected = paginatedTransactions.length > 0 &&
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
            {summary.count} transactions
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
          <p className="text-lg font-semibold text-red-600">
            {formatCurrency(summary.totalDebit)}
          </p>
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
                onClick={() => handleSort('date')}
              >
                <div className="flex items-center">
                  Date <SortIcon field="date" />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 sticky top-0 bg-neutral-50"
                onClick={() => handleSort('narrative')}
              >
                <div className="flex items-center">
                  Details <SortIcon field="narrative" />
                </div>
              </TableHead>
              <TableHead
                className="cursor-pointer hover:bg-neutral-100 sticky top-0 bg-neutral-50"
                onClick={() => handleSort('reconciliation_key')}
              >
                <div className="flex items-center">
                  Recon Key <SortIcon field="reconciliation_key" />
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
              <TableHead className="w-20 sticky top-0 bg-neutral-50"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedTransactions.length === 0 ? (
              <TableEmpty message="No unreconciled transactions" colSpan={6} />
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
                  <TableCell className="py-2 text-xs text-gray-500 whitespace-nowrap">
                    {txn.date ? formatDateTime(txn.date) : '-'}
                  </TableCell>
                  <TableCell
                    className="py-2 max-w-[150px] truncate text-xs"
                    title={txn.narrative || ''}
                  >
                    {txn.narrative || '-'}
                  </TableCell>
                  <TableCell
                    className="py-2 max-w-[120px] truncate text-xs font-mono text-gray-500"
                    title={txn.reconciliation_key || ''}
                  >
                    {txn.reconciliation_key || '-'}
                  </TableCell>
                  <TableCell className="py-2 text-right font-mono text-xs whitespace-nowrap">
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
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onReconcileClick(txn)}
                      className="text-xs px-2 py-1"
                    >
                      Reconcile
                    </Button>
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

interface SideBySideTransactionViewProps {
  byGateway: Record<string, UnreconciledTransaction[]>;
  selectedIds: Set<number>;
  onToggleSelection: (id: number) => void;
  onToggleAllInternal: (transactions: UnreconciledTransaction[]) => void;
  onToggleAllExternal: (transactions: UnreconciledTransaction[]) => void;
  onReconcileClick: (txn: UnreconciledTransaction) => void;
}

export function SideBySideTransactionView({
  byGateway,
  selectedIds,
  onToggleSelection,
  onToggleAllInternal,
  onToggleAllExternal,
  onReconcileClick,
}: SideBySideTransactionViewProps) {
  // Separate internal (*_internal) and external (*_external) transactions based on gateway suffix
  const { internalTransactions, externalTransactions, internalGateways, externalGateways } =
    useMemo(() => {
      const internal: UnreconciledTransaction[] = [];
      const external: UnreconciledTransaction[] = [];
      const intGateways: string[] = [];
      const extGateways: string[] = [];

      Object.entries(byGateway).forEach(([gateway, transactions]) => {
        const gatewayLower = gateway.toLowerCase();
        if (gatewayLower.endsWith('_internal')) {
          internal.push(...transactions);
          if (!intGateways.includes(gateway)) intGateways.push(gateway);
        } else if (gatewayLower.endsWith('_external')) {
          external.push(...transactions);
          if (!extGateways.includes(gateway)) extGateways.push(gateway);
        } else {
          // Fallback: if no suffix, treat as external
          external.push(...transactions);
          if (!extGateways.includes(gateway)) extGateways.push(gateway);
        }
      });

      return {
        internalTransactions: internal,
        externalTransactions: external,
        internalGateways: intGateways,
        externalGateways: extGateways,
      };
    }, [byGateway]);

  // Extract base gateway name (remove _internal or _external suffix)
  const getBaseGateway = (gateway: string) => {
    return gateway.replace(/_internal$/, '').replace(/_external$/, '');
  };

  const internalTitle = internalGateways.length > 0
    ? `Internal (${internalGateways.map(g => getBaseGateway(g)).join(', ')})`
    : 'Internal (Workpay)';

  const externalTitle = externalGateways.length > 0
    ? `External (${externalGateways.map(g => getBaseGateway(g)).join(', ')})`
    : 'External (Bank)';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[calc(100vh-300px)] min-h-[500px]">
      <TransactionPanel
        title={externalTitle}
        transactions={externalTransactions}
        selectedIds={selectedIds}
        onToggleSelection={onToggleSelection}
        onToggleAll={() => onToggleAllExternal(externalTransactions)}
        onReconcileClick={onReconcileClick}
        variant="external"
      />
      <TransactionPanel
        title={internalTitle}
        transactions={internalTransactions}
        selectedIds={selectedIds}
        onToggleSelection={onToggleSelection}
        onToggleAll={() => onToggleAllInternal(internalTransactions)}
        onReconcileClick={onReconcileClick}
        variant="internal"
      />
    </div>
  );
}
