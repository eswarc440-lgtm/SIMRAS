import {
  Link,
  Outlet,
  createRootRouteWithContext,
} from "@tanstack/react-router";

import type {
  QueryClient,
} from "@tanstack/react-query";

import {
  QueryClientProvider,
} from "@tanstack/react-query";

import {
  AuthProvider,
} from "@/hooks/useAuth";


function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="text-center">
        <h1 className="text-5xl font-bold">
          404
        </h1>

        <p className="mt-3 text-muted-foreground">
          Page not found.
        </p>

        <Link
          to="/"
          className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground"
        >
          Return to SIMRAS
        </Link>
      </div>
    </div>
  );
}


function RootError({
  error,
}: {
  error: Error;
}) {
  console.error(
    "SIMRAS FRONTEND ERROR:",
    error
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-6">
      <div className="max-w-xl rounded-lg border bg-card p-8">
        <h1 className="text-xl font-semibold">
          SIMRAS frontend error
        </h1>

        <p className="mt-3 break-words text-sm text-muted-foreground">
          {error?.message ||
            "Unknown frontend error"}
        </p>

        <a
          href="/"
          className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground"
        >
          Reload SIMRAS
        </a>
      </div>
    </div>
  );
}


export const Route =
  createRootRouteWithContext<{
    queryClient: QueryClient;
  }>()({
    component: RootComponent,
    notFoundComponent: NotFoundPage,
    errorComponent: RootError,
  });


function RootComponent() {
  const {
    queryClient,
  } = Route.useRouteContext();

  return (
    <QueryClientProvider
      client={queryClient}
    >
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </QueryClientProvider>
  );
}
