'use client';

import { useUser, useAuth, SignIn, UserButton } from '@clerk/nextjs';
import { useEffect, useState, useCallback } from 'react';

interface Application {
  name: string;
  description: string;
  url: string;
  roles: string[];
  admin?: boolean;
}

interface UserData {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface ApiResponse {
  user: UserData;
  applications: Application[];
  total_access: number;
}

export default function Home() {
  const { isSignedIn, user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const [userApps, setUserApps] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // const [debugInfo, setDebugInfo] = useState<string>('');

  const fetchUserApps = useCallback(async () => {
    if (!isSignedIn) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      console.log('User info:', { email: user?.emailAddresses?.[0]?.emailAddress, user });
      console.log('Token preview:', token?.substring(0, 50) + '...');
      
      const userEmail = user?.emailAddresses?.[0]?.emailAddress;
      const response = await fetch(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/api/apps`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-User-Email': userEmail || '',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch apps: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('API Response:', data);
      setUserApps(data);
    } catch (err) {
      console.error('Error fetching user apps:', err);
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    if (isSignedIn) {
      fetchUserApps();
    }
  }, [isSignedIn, fetchUserApps]);

  // Debug effect to track Clerk state (temporarily disabled)
  // useEffect(() => {
  //   const timer = setTimeout(() => {
  //     setDebugInfo(`isLoaded: ${isLoaded}, isSignedIn: ${isSignedIn}, publishableKey: ${process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? 'present' : 'missing'}`);
  //   }, 2000);
  //   return () => clearTimeout(timer);
  // }, [isLoaded, isSignedIn]);

  // Temporary: Skip isLoaded check and show debug info
  const showDebugPage = false; // Toggle this to debug

  if (showDebugPage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-lg">
          <h1 className="text-2xl font-bold mb-4">Debug Page</h1>
          <div className="p-4 bg-gray-100 rounded text-left mb-4">
            <p><strong>isLoaded:</strong> {String(isLoaded)}</p>
            <p><strong>isSignedIn:</strong> {String(isSignedIn)}</p>
            <p><strong>publishableKey present:</strong> {process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? 'Yes' : 'No'}</p>
            <p><strong>publishableKey value:</strong> {process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || 'undefined'}</p>
            <p><strong>publishableKey length:</strong> {process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.length || 0}</p>
            <p><strong>Key ends with:</strong> {process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.slice(-5) || 'N/A'}</p>
            <p><strong>User object:</strong> {user ? 'Present' : 'Null'}</p>
            <p><strong>Clerk JS loaded:</strong> {typeof window !== 'undefined' && (window as unknown as { Clerk?: unknown }).Clerk ? 'Yes' : 'No'}</p>
          </div>
          
          <div className="space-y-4">
            <button 
              onClick={() => {
                const clerk = (window as unknown as { Clerk?: { openSignIn?: () => void } }).Clerk;
                if (typeof window !== 'undefined' && clerk?.openSignIn) {
                  clerk.openSignIn();
                } else {
                  alert('Clerk not loaded yet');
                }
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              Try Sign In (Modal)
            </button>
            
            <button 
              onClick={() => window.location.href = '/'}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              Try Sign In (Redirect)
            </button>
            
            <button 
              onClick={() => {
                const clerk = (window as unknown as { Clerk?: { openSignIn?: () => void } }).Clerk;
                if (typeof window !== 'undefined' && clerk?.openSignIn) {
                  clerk.openSignIn();
                } else {
                  alert('Clerk not loaded yet');
                }
              }}
              className="w-full bg-yellow-600 hover:bg-yellow-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              Direct Clerk.openSignIn()
            </button>
          </div>
          
          <p className="mt-4 text-sm text-gray-600">
            This bypasses the isLoaded check to test if Clerk buttons work
          </p>
        </div>
      </div>
    );
  }

  // Show loading spinner while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Clerk...</p>
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-br from-blue-200/30 to-purple-200/30 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-tr from-indigo-200/30 to-pink-200/30 rounded-full blur-3xl"></div>
        </div>
        
        <div className="relative flex items-center justify-center min-h-screen p-4">
          <div className="w-full max-w-md">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mb-4 shadow-lg">
                <span className="text-2xl">🌴</span>
              </div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
                Mar Vista
              </h1>
              <p className="text-gray-600">
                Access your applications with secure authentication
              </p>
            </div>
            
            {/* Clerk Sign In Component */}
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8">
              <SignIn
                redirectUrl="/"
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "shadow-none border-0 bg-transparent",
                    headerTitle: "text-xl font-semibold text-gray-800",
                    headerSubtitle: "text-gray-600",
                    socialButtonsBlockButton: "bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 shadow-sm",
                    formFieldInput: "border-gray-200 focus:border-blue-500 focus:ring-blue-500",
                    formButtonPrimary: "bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg",
                    footerActionLink: "text-blue-600 hover:text-blue-700"
                  }
                }}
              />
            </div>
            
            {/* Footer */}
            <div className="text-center mt-6">
              <p className="text-sm text-gray-500">
                Secure authentication powered by Clerk
              </p>
            </div>
          </div>
        </div>
      </div>
    );
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
                Mar Vista
              </h1>
              {userApps?.user.role === 'SUPER_ADMIN' && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-sm">
                  ⚡ Super Admin
                </span>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                Welcome, {user?.firstName || user?.emailAddresses?.[0]?.emailAddress}
              </span>
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </div>
      </nav>

      <main className="relative max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {loading && (
            <div className="text-center">
              <div className="inline-flex items-center px-4 py-2 font-semibold leading-6 text-sm shadow rounded-md text-blue-500 bg-blue-100">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Loading your applications...
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-md bg-red-50 p-4 mb-6">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">
                    Error loading applications
                  </h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                  <div className="mt-4">
                    <button
                      onClick={fetchUserApps}
                      className="bg-red-100 px-2 py-1 text-sm font-medium text-red-800 rounded-md hover:bg-red-200"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {userApps && (
            <div>
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Your Applications
                </h2>
                <p className="text-gray-600">
                  You have access to {userApps.total_access} application{userApps.total_access !== 1 ? 's' : ''}
                  {userApps.user.role === 'SUPER_ADMIN' && ' with administrative privileges'}
                </p>
                <div className="mt-2 text-sm text-gray-500">
                  User: {userApps.user.email} | Role: {userApps.user.role}
                  <button 
                    onClick={async () => {
                      const token = await getToken();
                      const response = await fetch(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/api/debug`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                      });
                      const debug = await response.json();
                      console.log('Debug info:', debug);
                      alert(JSON.stringify(debug, null, 2));
                    }}
                    className="ml-4 text-blue-600 hover:text-blue-800 underline"
                  >
                    Debug Token
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {userApps.applications.map((app, index) => (
                  <div
                    key={index}
                    className={`group relative rounded-2xl border px-6 py-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 ${
                      app.admin 
                        ? 'border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100' 
                        : 'border-gray-200 bg-white/80 backdrop-blur-sm hover:bg-white'
                    }`}
                  >
                    <div className="flex items-start space-x-4">
                      <div className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center shadow-md ${
                        app.admin 
                          ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white' 
                          : 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-600'
                      }`}>
                        <span className="text-lg">
                          {app.admin ? '🛡️' : '🏢'}
                        </span>
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        {app.admin && (
                          <div className="mb-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-sm">
                              ⚡ Admin Access
                            </span>
                          </div>
                        )}
                        
                        {app.admin ? (
                          <button 
                            onClick={async () => {
                              const token = await getToken();
                              const userEmail = user?.emailAddresses?.[0]?.emailAddress;
                              
                              // Build admin URL with auth parameters
                              const adminUrl = new URL(app.url);
                              adminUrl.searchParams.set('token', token || '');
                              adminUrl.searchParams.set('email', userEmail || '');
                              
                              // Open admin interface in new window
                              window.open(adminUrl.toString(), '_blank');
                            }}
                            className="focus:outline-none w-full text-left"
                          >
                            <span className="absolute inset-0" aria-hidden="true" />
                            <h3 className={`text-lg font-semibold mb-2 group-hover:text-blue-600 transition-colors ${
                              app.admin ? 'text-blue-900' : 'text-gray-900'
                            }`}>
                              {app.name}
                            </h3>
                            <p className={`text-sm ${
                              app.admin ? 'text-blue-600' : 'text-gray-600'
                            }`}>
                              {app.description}
                            </p>
                          </button>
                        ) : (
                          <a href={app.url} className="focus:outline-none">
                            <span className="absolute inset-0" aria-hidden="true" />
                            <h3 className={`text-lg font-semibold mb-2 group-hover:text-blue-600 transition-colors ${
                              app.admin ? 'text-blue-900' : 'text-gray-900'
                            }`}>
                              {app.name}
                            </h3>
                            <p className={`text-sm ${
                              app.admin ? 'text-blue-600' : 'text-gray-600'
                            }`}>
                              {app.description}
                            </p>
                          </a>
                        )}
                        
                        <div className="mt-4 flex items-center justify-between">
                          <div className="flex items-center text-xs text-gray-500">
                            <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                            Active
                          </div>
                          <svg className="w-5 h-5 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {userApps.user.role === 'SUPER_ADMIN' && (
                <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-blue-900 mb-4">
                    Administrator Functions
                  </h3>
                  <div className="space-y-2">
                    <button
                      onClick={() => window.open(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/api/debug-db`, '_blank')}
                      className="mr-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                    >
                      View Database
                    </button>
                    <button
                      onClick={() => alert('User management UI coming soon!')}
                      className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
                    >
                      Manage Users
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}