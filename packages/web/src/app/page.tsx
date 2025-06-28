'use client';

import { useUser, useAuth, SignInButton, UserButton } from '@clerk/nextjs';
import { useEffect, useState, useCallback } from 'react';

interface Application {
  name: string;
  description: string;
  url: string;
  roles: string[];
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_COMMUNITY_AUTH_API}/api/apps`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch apps: ${response.statusText}`);
      }

      const data = await response.json();
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
            <SignInButton mode="modal">
              <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                Try Sign In (Modal)
              </button>
            </SignInButton>
            
            <SignInButton mode="redirect">
              <button className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                Try Sign In (Redirect)
              </button>
            </SignInButton>
            
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-md p-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Community Portal
            </h1>
            <p className="text-gray-600 mb-6">
              Sign in to access your community applications
            </p>
            <div className="space-y-4">
              <SignInButton mode="modal">
                <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors">
                  Sign In with Email, Google, or Apple
                </button>
              </SignInButton>
              <p className="text-xs text-gray-500 text-center">
                Secure authentication powered by Clerk
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                Community Portal
              </h1>
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

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
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
              <div className="mb-6">
                <h2 className="text-lg font-medium text-gray-900">
                  Your Applications
                </h2>
                <p className="mt-1 text-sm text-gray-600">
                  You have access to {userApps.total_access} application{userApps.total_access !== 1 ? 's' : ''}
                  {userApps.user.role === 'SUPER_ADMIN' && ' as Super Administrator'}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {userApps.applications.map((app, index) => (
                  <div
                    key={index}
                    className="relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm hover:border-gray-400"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex-1 min-w-0">
                        <a href={app.url} className="focus:outline-none">
                          <span className="absolute inset-0" aria-hidden="true" />
                          <p className="text-sm font-medium text-gray-900">
                            {app.name}
                          </p>
                          <p className="text-sm text-gray-500 truncate">
                            {app.description}
                          </p>
                        </a>
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