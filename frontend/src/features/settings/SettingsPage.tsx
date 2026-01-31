import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings,
  Calendar,
  Globe,
  Tag,
  Plus,
  Trash2,
  Edit2,
  X,
  RefreshCw,
  Database,
  Search,
  Cog,
} from 'lucide-react';
import { settingsApi, getErrorMessage } from '@/api';
import type {
  DateFormat,
  Country,
  ReconciliationKeyword,
  SystemSetting,
  DateFormatCreate,
  DateFormatUpdate,
  CountryCreate,
  CountryUpdate,
  CurrencyCreate,
  KeywordCreate,
  KeywordUpdate,
  SystemSettingCreate,
} from '@/api/settings';
import {
  Button,
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
  PageLoading,
  Alert,
  Input,
  Select,
  Modal,
  ModalFooter,
  Pagination,
} from '@/components/ui';
import { useIsUserRole } from '@/stores';

type TabType = 'date-formats' | 'countries' | 'keywords' | 'system';

const PAGE_SIZE = 10;

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('date-formats');
  const canEdit = useIsUserRole();
  const queryClient = useQueryClient();

  // Fetch all settings
  const { data: settings, isLoading, error, refetch } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.getAll(),
  });

  // Seed defaults mutation
  const seedMutation = useMutation({
    mutationFn: () => settingsApi.seedDefaults(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  const tabs = [
    { id: 'date-formats' as TabType, label: 'Date Formats', icon: Calendar },
    { id: 'countries' as TabType, label: 'Countries & Currencies', icon: Globe },
    { id: 'keywords' as TabType, label: 'Reconciliation Keywords', icon: Tag },
    { id: 'system' as TabType, label: 'System Settings', icon: Cog },
  ];

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading settings">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Settings className="h-6 w-6" />
            System Settings
          </h1>
          <p className="text-gray-500 mt-1">
            Configure date formats, countries, currencies, and reconciliation keywords
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {canEdit && (
            <Button
              variant="primary"
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
            >
              <Database className="h-4 w-4 mr-2" />
              {seedMutation.isPending ? 'Seeding...' : 'Seed Defaults'}
            </Button>
          )}
        </div>
      </div>

      {seedMutation.isSuccess && (
        <Alert variant="success" title="Defaults seeded successfully">
          {`Created: ${seedMutation.data.created.date_formats} date formats, ${seedMutation.data.created.countries} countries, ${seedMutation.data.created.currencies} currencies, ${seedMutation.data.created.keywords} keywords`}
        </Alert>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'date-formats' && settings && (
        <DateFormatsTab dateFormats={settings.date_formats} canEdit={canEdit} />
      )}
      {activeTab === 'countries' && settings && (
        <CountriesTab countries={settings.countries} canEdit={canEdit} />
      )}
      {activeTab === 'keywords' && settings && (
        <KeywordsTab keywords={settings.keywords} canEdit={canEdit} />
      )}
      {activeTab === 'system' && settings && (
        <SystemSettingsTab systemSettings={settings.system_settings} canEdit={canEdit} />
      )}
    </div>
  );
}

// =============================================================================
// Date Formats Tab
// =============================================================================

function DateFormatsTab({
  dateFormats,
  canEdit,
}: {
  dateFormats: DateFormat[];
  canEdit: boolean;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingFormat, setEditingFormat] = useState<DateFormat | null>(null);
  const [formData, setFormData] = useState<Omit<DateFormatCreate, 'display_name'>>({
    format_string: '',
    example: '',
    is_default: false,
  });
  const queryClient = useQueryClient();

  // Filter and paginate
  const filteredFormats = useMemo(() => {
    return dateFormats.filter(
      (f) =>
        f.format_string.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.example.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [dateFormats, searchTerm]);

  const totalPages = Math.ceil(filteredFormats.length / PAGE_SIZE);
  const paginatedFormats = filteredFormats.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  // Reset page when search changes
  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setCurrentPage(1);
  };

  const createMutation = useMutation({
    mutationFn: (data: DateFormatCreate) => settingsApi.dateFormats.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setShowAddModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: DateFormatUpdate }) =>
      settingsApi.dateFormats.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setEditingFormat(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => settingsApi.dateFormats.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  const resetForm = () => {
    setFormData({ format_string: '', example: '', is_default: false });
  };

  const openEditModal = (format: DateFormat) => {
    setEditingFormat(format);
    setFormData({
      format_string: format.format_string,
      example: format.example,
      is_default: format.is_default,
    });
  };

  const handleSubmit = () => {
    // Auto-generate display_name from format_string for backend compatibility
    const dataWithDisplayName = {
      ...formData,
      display_name: formData.format_string,
    };
    if (editingFormat) {
      updateMutation.mutate({ id: editingFormat.id, data: dataWithDisplayName });
    } else {
      createMutation.mutate(dataWithDisplayName);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Date Formats ({filteredFormats.length})</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search formats..."
                  className="pl-9 w-64"
                />
              </div>
              {canEdit && (
                <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Format
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Format String</TableHead>
                <TableHead>Example</TableHead>
                <TableHead>Status</TableHead>
                {canEdit && <TableHead className="w-28">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedFormats.length === 0 ? (
                <TableEmpty
                  message={searchTerm ? 'No formats match your search' : 'No date formats configured'}
                  colSpan={canEdit ? 4 : 3}
                />
              ) : (
                paginatedFormats.map((format) => (
                  <TableRow key={format.id}>
                    <TableCell className="font-mono text-sm">{format.format_string}</TableCell>
                    <TableCell className="text-gray-500">{format.example}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {format.is_default && <Badge variant="success">Default</Badge>}
                        {!format.is_active && <Badge variant="danger">Inactive</Badge>}
                      </div>
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEditModal(format)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteMutation.mutate(format.id)}
                            disabled={format.is_default || deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalItems={filteredFormats.length}
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={showAddModal || !!editingFormat}
        onClose={() => {
          setShowAddModal(false);
          setEditingFormat(null);
          resetForm();
        }}
        title={editingFormat ? 'Edit Date Format' : 'Add Date Format'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Format String</label>
            <Input
              value={formData.format_string}
              onChange={(e) => setFormData({ ...formData, format_string: e.target.value })}
              placeholder="%Y-%m-%d %H:%M:%S"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use format codes: %Y (year), %m (month), %d (day), %H (hour), %M (minute), %S (second)
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Example</label>
            <Input
              value={formData.example}
              onChange={(e) => setFormData({ ...formData, example: e.target.value })}
              placeholder="2026-01-28 07:20:32"
            />
            <p className="text-xs text-gray-500 mt-1">
              Show how a date/time looks in this format
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_default"
              checked={formData.is_default}
              onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="is_default" className="text-sm text-gray-700">
              Set as default format
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setShowAddModal(false);
              setEditingFormat(null);
              resetForm();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={
              !formData.format_string ||
              !formData.example ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {createMutation.isPending || updateMutation.isPending
              ? 'Saving...'
              : editingFormat
              ? 'Update'
              : 'Create'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

// =============================================================================
// Countries Tab
// =============================================================================

function CountriesTab({
  countries,
  canEdit,
}: {
  countries: Country[];
  canEdit: boolean;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddCountryModal, setShowAddCountryModal] = useState(false);
  const [editingCountry, setEditingCountry] = useState<Country | null>(null);
  const [addCurrencyToCountry, setAddCurrencyToCountry] = useState<Country | null>(null);
  const [countryFormData, setCountryFormData] = useState<CountryCreate>({ code: '', name: '' });
  const [currencyFormData, setCurrencyFormData] = useState<CurrencyCreate>({
    code: '',
    name: '',
    symbol: '',
    is_default: false,
  });
  const queryClient = useQueryClient();

  // Filter and paginate
  const filteredCountries = useMemo(() => {
    return countries.filter(
      (c) =>
        c.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [countries, searchTerm]);

  const totalPages = Math.ceil(filteredCountries.length / PAGE_SIZE);
  const paginatedCountries = filteredCountries.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setCurrentPage(1);
  };

  // Country mutations
  const createCountryMutation = useMutation({
    mutationFn: (data: CountryCreate) => settingsApi.countries.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setShowAddCountryModal(false);
      setCountryFormData({ code: '', name: '' });
    },
  });

  const updateCountryMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: CountryUpdate }) =>
      settingsApi.countries.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setEditingCountry(null);
      setCountryFormData({ code: '', name: '' });
    },
  });

  const deleteCountryMutation = useMutation({
    mutationFn: (id: number) => settingsApi.countries.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  // Currency mutations
  const addCurrencyMutation = useMutation({
    mutationFn: ({ countryId, data }: { countryId: number; data: CurrencyCreate }) =>
      settingsApi.countries.addCurrency(countryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setAddCurrencyToCountry(null);
      setCurrencyFormData({ code: '', name: '', symbol: '', is_default: false });
    },
  });

  const deleteCurrencyMutation = useMutation({
    mutationFn: (id: number) => settingsApi.currencies.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  const openEditCountryModal = (country: Country) => {
    setEditingCountry(country);
    setCountryFormData({ code: country.code, name: country.name });
  };

  const handleCountrySubmit = () => {
    if (editingCountry) {
      updateCountryMutation.mutate({ id: editingCountry.id, data: countryFormData });
    } else {
      createCountryMutation.mutate(countryFormData);
    }
  };

  const handleCurrencySubmit = () => {
    if (addCurrencyToCountry) {
      addCurrencyMutation.mutate({ countryId: addCurrencyToCountry.id, data: currencyFormData });
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Countries & Currencies ({filteredCountries.length})</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search countries..."
                  className="pl-9 w-64"
                />
              </div>
              {canEdit && (
                <Button variant="primary" size="sm" onClick={() => setShowAddCountryModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Country
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Currencies</TableHead>
                {canEdit && <TableHead className="w-36">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedCountries.length === 0 ? (
                <TableEmpty
                  message={searchTerm ? 'No countries match your search' : 'No countries configured'}
                  colSpan={canEdit ? 4 : 3}
                />
              ) : (
                paginatedCountries.map((country) => (
                  <TableRow key={country.id}>
                    <TableCell className="font-mono font-medium">{country.code}</TableCell>
                    <TableCell>{country.name}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {country.currencies.map((curr) => (
                          <Badge
                            key={curr.id}
                            variant={curr.is_default ? 'success' : 'info'}
                            className="flex items-center gap-1"
                          >
                            {curr.code} {curr.symbol && `(${curr.symbol})`}
                            {canEdit && (
                              <button
                                onClick={() => deleteCurrencyMutation.mutate(curr.id)}
                                className="ml-1 hover:text-red-500"
                                disabled={deleteCurrencyMutation.isPending}
                              >
                                <X className="h-3 w-3" />
                              </button>
                            )}
                          </Badge>
                        ))}
                        {canEdit && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-6 px-2"
                            onClick={() => setAddCurrencyToCountry(country)}
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEditCountryModal(country)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteCountryMutation.mutate(country.id)}
                            disabled={deleteCountryMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalItems={filteredCountries.length}
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>

      {/* Add/Edit Country Modal */}
      <Modal
        isOpen={showAddCountryModal || !!editingCountry}
        onClose={() => {
          setShowAddCountryModal(false);
          setEditingCountry(null);
          setCountryFormData({ code: '', name: '' });
        }}
        title={editingCountry ? 'Edit Country' : 'Add Country'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country Code</label>
            <Input
              value={countryFormData.code}
              onChange={(e) =>
                setCountryFormData({ ...countryFormData, code: e.target.value.toUpperCase() })
              }
              placeholder="KE"
              maxLength={3}
            />
            <p className="text-xs text-gray-500 mt-1">2-3 letter ISO country code</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Country Name</label>
            <Input
              value={countryFormData.name}
              onChange={(e) => setCountryFormData({ ...countryFormData, name: e.target.value })}
              placeholder="Kenya"
            />
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setShowAddCountryModal(false);
              setEditingCountry(null);
              setCountryFormData({ code: '', name: '' });
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleCountrySubmit}
            disabled={
              !countryFormData.code ||
              !countryFormData.name ||
              createCountryMutation.isPending ||
              updateCountryMutation.isPending
            }
          >
            {createCountryMutation.isPending || updateCountryMutation.isPending
              ? 'Saving...'
              : editingCountry
              ? 'Update'
              : 'Create'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Add Currency Modal */}
      <Modal
        isOpen={!!addCurrencyToCountry}
        onClose={() => {
          setAddCurrencyToCountry(null);
          setCurrencyFormData({ code: '', name: '', symbol: '', is_default: false });
        }}
        title={`Add Currency to ${addCurrencyToCountry?.name || ''}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Currency Code</label>
            <Input
              value={currencyFormData.code}
              onChange={(e) =>
                setCurrencyFormData({ ...currencyFormData, code: e.target.value.toUpperCase() })
              }
              placeholder="KES"
              maxLength={3}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Currency Name</label>
            <Input
              value={currencyFormData.name}
              onChange={(e) => setCurrencyFormData({ ...currencyFormData, name: e.target.value })}
              placeholder="Kenyan Shilling"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Symbol (optional)</label>
            <Input
              value={currencyFormData.symbol || ''}
              onChange={(e) => setCurrencyFormData({ ...currencyFormData, symbol: e.target.value })}
              placeholder="KSh"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="currency_default"
              checked={currencyFormData.is_default}
              onChange={(e) =>
                setCurrencyFormData({ ...currencyFormData, is_default: e.target.checked })
              }
              className="rounded border-gray-300"
            />
            <label htmlFor="currency_default" className="text-sm text-gray-700">
              Set as default currency for this country
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setAddCurrencyToCountry(null);
              setCurrencyFormData({ code: '', name: '', symbol: '', is_default: false });
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleCurrencySubmit}
            disabled={
              !currencyFormData.code || !currencyFormData.name || addCurrencyMutation.isPending
            }
          >
            {addCurrencyMutation.isPending ? 'Adding...' : 'Add Currency'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

// =============================================================================
// Keywords Tab
// =============================================================================

function KeywordsTab({
  keywords,
  canEdit,
}: {
  keywords: {
    charge: ReconciliationKeyword[];
    reversal: ReconciliationKeyword[];
  };
  canEdit: boolean;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'charge' | 'reversal'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingKeyword, setEditingKeyword] = useState<ReconciliationKeyword | null>(null);
  const [formData, setFormData] = useState<KeywordCreate>({
    keyword: '',
    keyword_type: 'charge',
    description: '',
    is_case_sensitive: false,
  });
  const queryClient = useQueryClient();

  // Flatten and filter keywords
  const allKeywords = useMemo(() => {
    const all = [
      ...keywords.charge.map((k) => ({ ...k, _type: 'charge' as const })),
      ...keywords.reversal.map((k) => ({ ...k, _type: 'reversal' as const })),
    ];
    return all.filter((k) => {
      const matchesSearch = k.keyword.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === 'all' || k.keyword_type === filterType;
      return matchesSearch && matchesType;
    });
  }, [keywords, searchTerm, filterType]);

  const totalPages = Math.ceil(allKeywords.length / PAGE_SIZE);
  const paginatedKeywords = allKeywords.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setCurrentPage(1);
  };

  const handleFilterChange = (type: 'all' | 'charge' | 'reversal') => {
    setFilterType(type);
    setCurrentPage(1);
  };

  const createMutation = useMutation({
    mutationFn: (data: KeywordCreate) => settingsApi.keywords.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setShowAddModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: KeywordUpdate }) =>
      settingsApi.keywords.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setEditingKeyword(null);
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => settingsApi.keywords.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  const resetForm = () => {
    setFormData({ keyword: '', keyword_type: 'charge', description: '', is_case_sensitive: false });
  };

  const openEditModal = (keyword: ReconciliationKeyword) => {
    setEditingKeyword(keyword);
    setFormData({
      keyword: keyword.keyword,
      keyword_type: keyword.keyword_type,
      description: keyword.description || '',
      is_case_sensitive: keyword.is_case_sensitive,
    });
  };

  const handleSubmit = () => {
    if (editingKeyword) {
      updateMutation.mutate({ id: editingKeyword.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const getTypeBadgeVariant = (type: string) => {
    switch (type) {
      case 'charge':
        return 'warning';
      case 'reversal':
        return 'danger';
      default:
        return 'info';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'charge':
        return 'Charge';
      case 'reversal':
        return 'Reversal';
      default:
        return type;
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Reconciliation Keywords ({allKeywords.length})</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search keywords..."
                  className="pl-9 w-48"
                />
              </div>
              <Select
                value={filterType}
                onChange={(e) =>
                  handleFilterChange(e.target.value as 'all' | 'charge' | 'reversal')
                }
                options={[
                  { value: 'all', label: 'All Types' },
                  { value: 'charge', label: 'Charges' },
                  { value: 'reversal', label: 'Reversals' },
                ]}
                className="w-40"
              />
              {canEdit && (
                <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Keyword
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Keyword</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Case Sensitive</TableHead>
                <TableHead>Status</TableHead>
                {canEdit && <TableHead className="w-28">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedKeywords.length === 0 ? (
                <TableEmpty
                  message={
                    searchTerm || filterType !== 'all'
                      ? 'No keywords match your filters'
                      : 'No keywords configured'
                  }
                  colSpan={canEdit ? 6 : 5}
                />
              ) : (
                paginatedKeywords.map((keyword) => (
                  <TableRow key={keyword.id}>
                    <TableCell className="font-medium">{keyword.keyword}</TableCell>
                    <TableCell>
                      <Badge variant={getTypeBadgeVariant(keyword.keyword_type)}>
                        {getTypeLabel(keyword.keyword_type)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-500 max-w-xs truncate">
                      {keyword.description || '-'}
                    </TableCell>
                    <TableCell>
                      {keyword.is_case_sensitive ? (
                        <Badge variant="info">Yes</Badge>
                      ) : (
                        <span className="text-gray-400">No</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {!keyword.is_active && <Badge variant="danger">Inactive</Badge>}
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="outline" size="sm" onClick={() => openEditModal(keyword)}>
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteMutation.mutate(keyword.id)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalItems={allKeywords.length}
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>

      {/* Add/Edit Keyword Modal */}
      <Modal
        isOpen={showAddModal || !!editingKeyword}
        onClose={() => {
          setShowAddModal(false);
          setEditingKeyword(null);
          resetForm();
        }}
        title={editingKeyword ? 'Edit Keyword' : 'Add Keyword'}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Keyword</label>
            <Input
              value={formData.keyword}
              onChange={(e) => setFormData({ ...formData, keyword: e.target.value })}
              placeholder="Enter keyword..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <Select
              value={formData.keyword_type}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  keyword_type: e.target.value as 'charge' | 'reversal',
                })
              }
              options={[
                { value: 'charge', label: 'Charge - Bank fees, commissions, levies' },
                { value: 'reversal', label: 'Reversal - Transaction reversals, refunds' },
              ]}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description (optional)
            </label>
            <Input
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Brief description of this keyword..."
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="case_sensitive"
              checked={formData.is_case_sensitive}
              onChange={(e) => setFormData({ ...formData, is_case_sensitive: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="case_sensitive" className="text-sm text-gray-700">
              Case sensitive matching
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setShowAddModal(false);
              setEditingKeyword(null);
              resetForm();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!formData.keyword || createMutation.isPending || updateMutation.isPending}
          >
            {createMutation.isPending || updateMutation.isPending
              ? 'Saving...'
              : editingKeyword
              ? 'Update'
              : 'Create'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}

// =============================================================================
// System Settings Tab
// =============================================================================

function SystemSettingsTab({
  systemSettings,
  canEdit,
}: {
  systemSettings: SystemSetting[];
  canEdit: boolean;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSetting, setEditingSetting] = useState<SystemSetting | null>(null);
  const [editValue, setEditValue] = useState('');
  const [formData, setFormData] = useState<SystemSettingCreate>({
    key: '',
    value: '',
    value_type: 'string',
    description: '',
    is_editable: true,
  });
  const queryClient = useQueryClient();

  // Filter and paginate
  const filteredSettings = useMemo(() => {
    return systemSettings.filter(
      (s) =>
        s.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (s.description || '').toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [systemSettings, searchTerm]);

  const totalPages = Math.ceil(filteredSettings.length / PAGE_SIZE);
  const paginatedSettings = filteredSettings.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setCurrentPage(1);
  };

  const createMutation = useMutation({
    mutationFn: (data: SystemSettingCreate) => settingsApi.system.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setShowAddModal(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsApi.system.update(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
      setEditingSetting(null);
      setEditValue('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (key: string) => settingsApi.system.delete(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'], refetchType: 'all' });
    },
  });

  const resetForm = () => {
    setFormData({
      key: '',
      value: '',
      value_type: 'string',
      description: '',
      is_editable: true,
    });
  };

  const openEditModal = (setting: SystemSetting) => {
    setEditingSetting(setting);
    setEditValue(setting.value || '');
  };

  const handleSubmitCreate = () => {
    createMutation.mutate(formData);
  };

  const handleSubmitUpdate = () => {
    if (editingSetting) {
      updateMutation.mutate({ key: editingSetting.key, value: editValue });
    }
  };

  const formatValue = (setting: SystemSetting) => {
    if (!setting.value) return <span className="text-gray-400">Not set</span>;
    if (setting.value_type === 'boolean') {
      return setting.value === 'true' ? (
        <Badge variant="success">Enabled</Badge>
      ) : (
        <Badge variant="danger">Disabled</Badge>
      );
    }
    return setting.value;
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>System Settings ({filteredSettings.length})</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search settings..."
                  className="pl-9 w-64"
                />
              </div>
              {canEdit && (
                <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Setting
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                {canEdit && <TableHead className="w-28">Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedSettings.length === 0 ? (
                <TableEmpty
                  message={
                    searchTerm ? 'No settings match your search' : 'No system settings configured. Click "Add Setting" to create one.'
                  }
                  colSpan={canEdit ? 5 : 4}
                />
              ) : (
                paginatedSettings.map((setting) => (
                  <TableRow key={setting.id}>
                    <TableCell className="font-mono text-sm">{setting.key}</TableCell>
                    <TableCell>{formatValue(setting)}</TableCell>
                    <TableCell>
                      <Badge variant="info">{setting.value_type}</Badge>
                    </TableCell>
                    <TableCell className="text-gray-500 max-w-xs truncate">
                      {setting.description || '-'}
                    </TableCell>
                    {canEdit && (
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEditModal(setting)}
                            disabled={!setting.is_editable}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (confirm(`Delete setting "${setting.key}"?`)) {
                                deleteMutation.mutate(setting.key);
                              }
                            }}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
            totalItems={filteredSettings.length}
            pageSize={PAGE_SIZE}
          />
        </CardContent>
      </Card>

      {/* Add Setting Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          resetForm();
        }}
        title="Add New System Setting"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Key *</label>
            <Input
              value={formData.key}
              onChange={(e) => setFormData({ ...formData, key: e.target.value })}
              placeholder="e.g., max_upload_size"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use lowercase with underscores (e.g., feature_enabled, max_items)
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Value Type</label>
            <Select
              value={formData.value_type || 'string'}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  value_type: e.target.value as 'string' | 'number' | 'boolean' | 'json',
                })
              }
              options={[
                { value: 'string', label: 'String (text)' },
                { value: 'number', label: 'Number' },
                { value: 'boolean', label: 'Boolean (true/false)' },
                { value: 'json', label: 'JSON (complex data)' },
              ]}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
            {formData.value_type === 'boolean' ? (
              <Select
                value={formData.value || 'true'}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                options={[
                  { value: 'true', label: 'Enabled (true)' },
                  { value: 'false', label: 'Disabled (false)' },
                ]}
              />
            ) : (
              <Input
                value={formData.value || ''}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                placeholder={
                  formData.value_type === 'json'
                    ? '{"key": "value"}'
                    : formData.value_type === 'number'
                    ? '0'
                    : 'Enter value...'
                }
                type={formData.value_type === 'number' ? 'number' : 'text'}
              />
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <Input
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Brief description of what this setting controls"
            />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_editable"
              checked={formData.is_editable !== false}
              onChange={(e) => setFormData({ ...formData, is_editable: e.target.checked })}
              className="rounded border-gray-300"
            />
            <label htmlFor="is_editable" className="text-sm text-gray-700">
              Allow editing after creation
            </label>
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setShowAddModal(false);
              resetForm();
            }}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmitCreate}
            disabled={!formData.key || createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create Setting'}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Edit Setting Modal */}
      <Modal
        isOpen={!!editingSetting}
        onClose={() => {
          setEditingSetting(null);
          setEditValue('');
        }}
        title={`Edit Setting: ${editingSetting?.key || ''}`}
      >
        <div className="space-y-4">
          {editingSetting?.description && (
            <p className="text-sm text-gray-600">{editingSetting.description}</p>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
            {editingSetting?.value_type === 'boolean' ? (
              <Select
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                options={[
                  { value: 'true', label: 'Enabled' },
                  { value: 'false', label: 'Disabled' },
                ]}
              />
            ) : (
              <Input
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                placeholder="Enter value..."
                type={editingSetting?.value_type === 'number' ? 'number' : 'text'}
              />
            )}
            <p className="text-xs text-gray-500 mt-1">Type: {editingSetting?.value_type}</p>
          </div>
        </div>
        <ModalFooter>
          <Button
            variant="outline"
            onClick={() => {
              setEditingSetting(null);
              setEditValue('');
            }}
          >
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmitUpdate} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? 'Saving...' : 'Update'}
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}
