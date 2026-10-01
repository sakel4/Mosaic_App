import { Routes } from '@angular/router';
import { Dashboard } from './pages/dashboard/dashboard';
import { AppLayout } from './layout/app-layout/app-layout';
import { Practice } from './pages/practice/practice';
import { Progress } from './pages/progress/progress';
import { RealWorld } from './pages/real-world/real-world';
import { Auth } from './pages/auth/auth';
import { Profile } from './pages/profile/profile';
import { authGuard } from './core/guards/auth-guard';
import { Assessment } from './pages/assessment/assessment';
import { Onboarding } from './pages/onboarding/onboarding';


export const routes: Routes = [
    // Shown inside the layout (layout's <router-outlet>)
    {
        path: '',
        component: AppLayout,
        canActivate: [authGuard],
        children: [
            { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
            { path: 'dashboard', component: Dashboard },
            { path: 'practice', component: Practice },
            { path: 'progress', component: Progress },
            { path: 'real-world', component: RealWorld },
            { path: 'profile', component: Profile}
        ],
    },

    // Outside the layout (rendered directly in app.html's <router-outlet>)
    { path: 'login', component: Auth, data: { mode: 'login' } },
    { path: 'assessment', component: Assessment },
    { path: 'onboarding', component: Onboarding},
    { path: 'register', component: Auth, data: { mode: 'register' } },
    { path: 'auth', redirectTo: 'login', pathMatch: 'full' },
    { path: '**', redirectTo: '' },
];
