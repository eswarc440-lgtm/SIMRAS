import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Link, Outlet, createRootRouteWithContext, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { AuthProvider } from "../hooks/useAuth";

function NotFoundComponent() {
  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold">404</h1>
        <p className="mt-3 text-muted-foreground">Page not found.</p>
        <Link to="/dashboard" className="mt-5 inline-flex rounded-md bg-primary px-4 py-2 text-primary-foreground">Dashboard</Link>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  useEffect(() => console.error(error), [error]);
  return (
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold">This page did not load</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <button className="mt-5 rounded-md bg-primary px-4 py-2 text-primary-foreground" onClick={() => { router.invalidate(); reset(); }}>Try again</button>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </QueryClientProvider>
  );
}
