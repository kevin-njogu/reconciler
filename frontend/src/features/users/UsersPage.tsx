import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, MoreVertical, UserX, UserCheck, Key, Trash2 } from 'lucide-react';
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
import type { User, UserRole } from '@/types';

export function UsersPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isSuperAdmin = useIsSuperAdmin();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isResetPasswordModalOpen, setIsResetPasswordModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<number | null>(null);

  // Form state
  const [newUser, setNewUser] = useState({ first_name: '', last_name: '', email: '', password: '', role: 'user' as UserRole });
  const [newPassword, setNewPassword] = useState('');

  const { data: users, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.list(),
  });

  const createUserMutation = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User created successfully');
      setIsCreateModalOpen(false);
      setNewUser({ first_name: '', last_name: '', email: '', password: '', role: 'user' });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const blockUserMutation = useMutation({
    mutationFn: usersApi.block,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User blocked successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const unblockUserMutation = useMutation({
    mutationFn: usersApi.unblock,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User unblocked successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const deactivateUserMutation = useMutation({
    mutationFn: usersApi.deactivate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deactivated successfully');
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: number; password: string }) =>
      usersApi.resetPassword(userId, password),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('Password reset successfully');
      setIsResetPasswordModalOpen(false);
      setNewPassword('');
      setSelectedUser(null);
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const handleCreateUser = () => {
    createUserMutation.mutate(newUser);
  };

  const handleResetPassword = () => {
    if (selectedUser && newPassword) {
      resetPasswordMutation.mutate({ userId: selectedUser.id, password: newPassword });
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
                    <TableCell className="font-medium">
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
        description="Add a new user to the system"
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
            label="Initial Password"
            type="password"
            value={newUser.password}
            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            placeholder="Enter initial password"
          />
          <Select
            label="Role"
            value={newUser.role}
            onChange={(e) => setNewUser({ ...newUser, role: e.target.value as UserRole })}
            options={roleOptions}
          />
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

      {/* Reset Password Modal */}
      <Modal
        isOpen={isResetPasswordModalOpen}
        onClose={() => {
          setIsResetPasswordModalOpen(false);
          setNewPassword('');
          setSelectedUser(null);
        }}
        title="Reset Password"
        description={`Reset password for user: ${selectedUser?.username}`}
      >
        <div className="space-y-4">
          <Input
            label="New Password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Enter new password"
          />
          <Alert variant="info">
            The user will be required to change their password on next login.
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
    </div>
  );
}
