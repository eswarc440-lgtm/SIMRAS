import { createFileRoute } from '@tanstack/react-router'
import { InspectionsPage } from '../pages/infrastructure/InspectionsPage'

export const Route = createFileRoute('/infrastructure/inspections')({
  head: () => ({
    meta: [
      { title: 'Inspections — SIMRAS' },
      { name: 'description', content: 'Asset inspection records and history.' },
      { property: 'og:title', content: 'Inspections — SIMRAS' },
      { property: 'og:description', content: 'Asset inspection records and history.' },
    ],
  }),
  component: InspectionsPage,
})
