import { Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';
import { AppLayout } from './layout/app-layout/app-layout';
import { Practice } from './pages/practice/practice';
import { Progress } from './pages/progress/progress';
import { RealWorld } from './pages/real-world/real-world';
import { Auth } from './pages/auth/auth';

export const routes: Routes = [
    // Shown inside the layout (layout's <router-outlet>)
    {
        path: '',
        component: AppLayout,
        children: [
            { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
            { path: 'dashboard', component: Dashboard },
            { path: 'practice', component: Practice },
            { path: 'progress', component: Progress },
            { path: 'real-world', component: RealWorld },
            { path: 'profile', component: Auth },
        ],
    },

    // Outside the layout (rendered directly in app.html's <router-outlet>)
    { path: 'auth', component: Auth },
    { path: '**', redirectTo: '' },
];
