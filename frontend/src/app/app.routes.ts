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
import { AssessedGuard } from './core/guards/assessed-guard';
import { OnboardedGuard } from './core/guards/onboarded-guard';
import { guestGuard } from './core/guards/guest-guard';


export const routes: Routes = [
    // Shown inside the layout (layout's <router-outlet>)
    {
        path: '',
        component: AppLayout,
        canActivate: [authGuard],
        canActivateChild: [authGuard, AssessedGuard],
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
    { path: 'login', component: Auth, data: { mode: 'login'}, canActivate: [guestGuard] },
    { path: 'assessment', component: Assessment, canActivate: [authGuard]},
    { path: 'onboarding', component: Onboarding, canActivate: [authGuard]},
    { path: 'register', component: Auth, data: { mode: 'register'}, canActivate: [guestGuard]},
    { path: 'auth', redirectTo: 'login', pathMatch: 'full' },
    { path: '**', redirectTo: '' },
];
