import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';

import { BiasRankingPage } from '../../pages/bias-ranking';
import { EventsPage } from '../../pages/events';
import { SingleEventPage } from '../../pages/single-event';
import { AppShell } from '../../widgets/app-shell';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/events" replace /> },
      { path: 'events', element: <EventsPage /> },
      { path: 'events/:eventId', element: <SingleEventPage /> },
      { path: 'ranking', element: <BiasRankingPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}
