'use client';

import { useUser, useAuth } from '@clerk/nextjs';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id: string;
  email: string;
  role: string;
  status: string;
  app_roles?: Record<string, string>;
}

interface UsersResponse {
  users: User[];
  total: number;
  error?: string;
}

export default function AdminPage() {
  const { isSignedIn, user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if user is superadmin
  const isAdmin = user?.emailAddresses?.[0]?.emailAddress === 'jacob@reider.us';

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/');
    }
    if (isLoaded && isSignedIn && !isAdmin) {
      router.push('/');
    }
  }, [isLoaded, isSignedIn, isAdmin, router]);

  const makeAuthenticatedRequest = async (url: string, options: RequestInit = {}) => {
    const token = await getToken();
    const userEmail = user?.emailAddresses?.[0]?.emailAddress;
    
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-User-Email': userEmail || '',
        ...options.headers,
      },
    });
  };

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await makeAuthenticatedRequest(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/admin/api/users`);
      const data: UsersResponse = await response.json();
      
      if (data.error) {
        setError(data.error);
      } else {
        setUsers(data.users);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const addUser = async () => {
    const email = prompt('Enter user email to add:');
    if (!email) return;
    
    const role = prompt('Enter role (USER, ADMIN, SUPER_ADMIN):', 'USER');
    if (!role) return;
    
    try {
      const response = await makeAuthenticatedRequest(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/admin/api/users`, {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      });
      
      const data = await response.json();
      if (data.error) {
        alert('Error: ' + data.error);
      } else {
        alert(`User added successfully: ${data.user.email} (${data.user.role})`);
        fetchUsers(); // Refresh the list
      }
    } catch (err) {
      alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const manageArcAccess = async () => {
    const email = prompt('Enter user email to manage ARC access:');
    if (!email) return;
    
    const role = prompt('Enter ARC role (owner, reviewer, admin):', 'reviewer');
    if (!role) return;
    
    try {
      const response = await makeAuthenticatedRequest(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/admin/api/user-roles`, {
        method: 'POST',
        body: JSON.stringify({ email, app: 'arc', role }),
      });
      
      const data = await response.json();
      if (data.error) {
        alert('Error: ' + data.error);
      } else {
        alert(`ARC role updated successfully: ${data.user.email} is now ${data.role} in ARC`);
        fetchUsers(); // Refresh the list
      }
    } catch (err) {
      alert('Error: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isSignedIn || !isAdmin) {
    return null; // Will redirect
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-blue-200/20 to-purple-200/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-indigo-200/20 to-pink-200/20 rounded-full blur-3xl"></div>
      </div>
      
      <nav className="relative bg-white/80 backdrop-blur-sm shadow-sm border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-md">
                <span className="text-sm">🌴</span>
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Mar Vista Admin
              </h1>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-sm">
                🛡️ Super Admin
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/')}
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                ← Back to Mar Vista Portal
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="relative max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">🌴 Mar Vista User Management</h2>
            <div className="bg-blue-50 p-4 rounded-lg mb-6">
              <p><strong>Superadmin:</strong> jacob@reider.us</p>
              <p><strong>System:</strong> MVAuth2 Centralized Authentication</p>
            </div>
          </div>

          {/* User Management Section */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8 mb-8">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">User Management</h3>
            <p className="text-gray-600 mb-6">Manage users across all Mar Vista applications</p>
            
            <div className="flex flex-wrap gap-4 mb-6">
              <button
                onClick={fetchUsers}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'View All Users'}
              </button>
              <button
                onClick={addUser}
                className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Add New User
              </button>
              <button
                onClick={manageArcAccess}
                className="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Manage ARC Access
              </button>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                <p className="text-red-800">Error: {error}</p>
              </div>
            )}

            {users.length > 0 && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">App Roles</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{user.email}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.role}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {user.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {user.app_roles ? (
                            <div className="space-y-1">
                              {Object.entries(user.app_roles).map(([app, role]) => (
                                <span key={app} className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-100 text-blue-800 mr-1">
                                  {app}: {role}
                                </span>
                              ))}
                            </div>
                          ) : (
                            '-'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* System Information */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">System Information</h3>
            <p className="text-gray-600 mb-6">Current system status and configuration</p>
            
            <div className="flex flex-wrap gap-4">
              <a
                href={`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/api`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                API Status
              </a>
              <a
                href={`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                API Documentation
              </a>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}