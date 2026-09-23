import { createFileRoute } from '@tanstack/react-router'
import { MaintenancePage } from '../pages/infrastructure/MaintenancePage'

export const Route = createFileRoute('/infrastructure/maintenance')({
  head: () => ({
    meta: [
      { title: 'Maintenance — SIMRAS' },
      { name: 'description', content: 'Asset maintenance tracking and work orders.' },
      { property: 'og:title', content: 'Maintenance — SIMRAS' },
      { property: 'og:description', content: 'Asset maintenance tracking and work orders.' },
    ],
  }),
  component: MaintenancePage,
})
