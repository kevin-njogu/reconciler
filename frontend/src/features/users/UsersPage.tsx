import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, MoreVertical, UserX, UserCheck, Key, Trash2, Copy, Check } from 'lucide-react';
import { usersApi, getErrorMessage } from '@/api';
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
  getStatusBadgeVariant,
  PageLoading,
  Alert,
  Modal,
  ModalFooter,
  Input,
  Select,
} from '@/components/ui';
import { useToast } from '@/hooks/useToast';
import { useIsSuperAdmin } from '@/stores';
import { formatDateTime } from '@/lib/utils';
import type { User, UserRole, UserCreateRequest } from '@/types';

export function UsersPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isSuperAdmin = useIsSuperAdmin();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isResetPasswordModalOpen, setIsResetPasswordModalOpen] = useState(false);
  const [isCredentialsModalOpen, setIsCredentialsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<number | null>(null);
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [generatedEmail, setGeneratedEmail] = useState('');
  const [copied, setCopied] = useState(false);

  // Form state - no password field (auto-generated)
  const [newUser, setNewUser] = useState({
    first_name: '',
    last_name: '',
    email: '',
    mobile_number: '',
    role: 'user' as UserRole,
  });

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
  });

  const createUserMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['users'], refetchType: 'all' });
      setIsCreateModalOpen(false);
      // Show the generated credentials
      setGeneratedEmail(newUser.email);
      setGeneratedPassword(data.initial_password);
      setIsCredentialsModalOpen(true);
      setNewUser({ first_name: '', last_name: '', email: '', mobile_number: '', role: 'user' });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const blockUserMutation = useMutation({
    mutationFn: usersApi.block,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'], refetchType: 'all' });
      toast.success('User blocked successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const unblockUserMutation = useMutation({
    mutationFn: usersApi.unblock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'], refetchType: 'all' });
      toast.success('User unblocked successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const deactivateUserMutation = useMutation({
    mutationFn: usersApi.deactivate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'], refetchType: 'all' });
      toast.success('User deactivated successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: (userId: number) => usersApi.resetPassword(userId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['users'], refetchType: 'all' });
      setIsResetPasswordModalOpen(false);
      // Show the new generated credentials
      setGeneratedEmail(selectedUser?.email || '');
      setGeneratedPassword(data.initial_password);
      setIsCredentialsModalOpen(true);
      setSelectedUser(null);
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleCreateUser = () => {
    const payload: UserCreateRequest = {
      first_name: newUser.first_name,
      last_name: newUser.last_name,
      email: newUser.email,
      role: newUser.role,
    };
    if (newUser.mobile_number.trim()) {
      payload.mobile_number = newUser.mobile_number.trim();
    }
    createUserMutation.mutate(payload);
  };

  const handleResetPassword = () => {
    if (selectedUser) {
      resetPasswordMutation.mutate(selectedUser.id);
    }
  };

  const handleCopyPassword = async () => {
    try {
      await navigator.clipboard.writeText(generatedPassword);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const roleOptions = [
    { value: 'user', label: 'User' },
    { value: 'admin', label: 'Admin' },
    ...(isSuperAdmin ? [{ value: 'super_admin', label: 'Super Admin' }] : []),
  ];

  if (isLoading) return <PageLoading />;

  if (error) {
    return (
      <Alert variant="error" title="Error loading users">
        {getErrorMessage(error)}
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-gray-500 mt-1">Manage system users and their access</p>
        </div>
        {isSuperAdmin && (
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create User
          </Button>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead className="w-10"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users?.length === 0 ? (
                <TableEmpty message="No users found" colSpan={6} />
              ) : (
                users?.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      {user.first_name && user.last_name
                        ? `${user.first_name} ${user.last_name}`
                        : user.first_name || user.last_name || '-'}
                    </TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(user.role)}>
                        {user.role.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(user.status)}>
                        {user.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {user.last_login_at ? formatDateTime(user.last_login_at) : 'Never'}
                    </TableCell>
                    <TableCell>
                      <div className="relative">
                        <button
                          onClick={() => setActiveDropdown(activeDropdown === user.id ? null : user.id)}
                          className="p-1 rounded hover:bg-gray-100"
                        >
                          <MoreVertical className="h-5 w-5 text-gray-500" />
                        </button>
                        {activeDropdown === user.id && (
                          <>
                            <div
                              className="fixed inset-0 z-10"
                              onClick={() => setActiveDropdown(null)}
                            />
                            <div className="absolute right-0 z-20 mt-1 w-48 rounded-lg bg-white py-1 shadow-lg ring-1 ring-black/5">
                              <button
                                onClick={() => {
                                  setSelectedUser(user);
                                  setIsResetPasswordModalOpen(true);
                                  setActiveDropdown(null);
                                }}
                                className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                              >
                                <Key className="h-4 w-4" />
                                Reset Password
                              </button>
                              {user.status === 'active' ? (
                                <button
                                  onClick={() => {
                                    blockUserMutation.mutate(user.id);
                                    setActiveDropdown(null);
                                  }}
                                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-orange-600 hover:bg-orange-50"
                                >
                                  <UserX className="h-4 w-4" />
                                  Block User
                                </button>
                              ) : user.status === 'blocked' ? (
                                <button
                                  onClick={() => {
                                    unblockUserMutation.mutate(user.id);
                                    setActiveDropdown(null);
                                  }}
                                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-green-600 hover:bg-green-50"
                                >
                                  <UserCheck className="h-4 w-4" />
                                  Unblock User
                                </button>
                              ) : null}
                              {isSuperAdmin && user.status !== 'deactivated' && (
                                <button
                                  onClick={() => {
                                    if (confirm('Are you sure? This action cannot be undone.')) {
                                      deactivateUserMutation.mutate(user.id);
                                    }
                                    setActiveDropdown(null);
                                  }}
                                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                                >
                                  <Trash2 className="h-4 w-4" />
                                  Deactivate
                                </button>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create User Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New User"
        description="Add a new user to the system. A password will be auto-generated and sent via email."
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name"
              value={newUser.first_name}
              onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })}
              placeholder="Enter first name"
            />
            <Input
              label="Last Name"
              value={newUser.last_name}
              onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })}
              placeholder="Enter last name"
            />
          </div>
          <Input
            label="Email"
            type="email"
            value={newUser.email}
            onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
            placeholder="Enter email"
          />
          <Input
            label="Mobile Number (optional)"
            type="tel"
            value={newUser.mobile_number}
            onChange={(e) => setNewUser({ ...newUser, mobile_number: e.target.value })}
            placeholder="+254712345678"
          />
          <Select
            label="Role"
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value as UserRole })}
            options={roleOptions}
          />
          <Alert variant="info">
            A secure password will be auto-generated and sent to the user via welcome email along with login instructions.
          </Alert>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateUser} isLoading={createUserMutation.isPending}>
            Create User
          </Button>
        </ModalFooter>
      </Modal>

      {/* Reset Password Confirmation Modal */}
      <Modal
        isOpen={isResetPasswordModalOpen}
        onClose={() => {
          setIsResetPasswordModalOpen(false);
          setSelectedUser(null);
        }}
        title="Reset Password"
        description={`Reset password for: ${selectedUser?.email}`}
      >
        <div className="space-y-4">
          <Alert variant="warning">
            This will generate a new password and send it to the user via email. The user will be required to change their password on next login.
          </Alert>
        </div>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsResetPasswordModalOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleResetPassword} isLoading={resetPasswordMutation.isPending}>
            Reset Password
          </Button>
        </ModalFooter>
      </Modal>

      {/* Generated Credentials Modal (one-time display) */}
      <Modal
        isOpen={isCredentialsModalOpen}
        onClose={() => {
          setIsCredentialsModalOpen(false);
          setGeneratedPassword('');
          setGeneratedEmail('');
          setCopied(false);
        }}
        title="User Credentials"
        description="Save this password now — it will not be shown again."
      >
        <div className="space-y-4">
          <Alert variant="warning">
            This password is shown only once. Make sure to save it or confirm the user received the welcome email.
          </Alert>

          <div className="bg-neutral-50 rounded-lg p-4 space-y-3">
            <div>
              <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Email</p>
              <p className="text-sm font-mono text-neutral-800 mt-1">{generatedEmail}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Password</p>
              <div className="flex items-center gap-2 mt-1">
                <code className="text-sm font-mono text-neutral-800 bg-white px-3 py-1.5 rounded border border-neutral-200 flex-1">
                  {generatedPassword}
                </code>
                <button
                  onClick={handleCopyPassword}
                  className="p-1.5 rounded hover:bg-neutral-200 text-neutral-500 transition-colors"
                  title="Copy password"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>

          <Alert variant="info">
            A welcome email has been sent to the user with their login credentials.
          </Alert>
        </div>
        <ModalFooter>
          <Button
            onClick={() => {
              setIsCredentialsModalOpen(false);
              setGeneratedPassword('');
              setGeneratedEmail('');
              setCopied(false);
            }}
          >
            Done
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}
