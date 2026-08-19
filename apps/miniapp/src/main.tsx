import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import { createQueryClient } from '@/app/queryClient';
import { createRouter } from '@/app/router';

import './index.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('в index.html нет элемента #root');
}

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={createRouter()} />
    </QueryClientProvider>
  </StrictMode>,
);
