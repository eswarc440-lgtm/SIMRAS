import {
  QueryClient,
} from "@tanstack/react-query";

import {
  createRouter,
} from "@tanstack/react-router";

import {
  routeTree,
} from "./routeTree.gen";


const queryClient =
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });


export const router =
  createRouter({
    routeTree,
    context: {
      queryClient,
    },
    scrollRestoration: true,
    defaultPreload: "intent",
  });


declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}


export function getRouter() {
  return router;
}
