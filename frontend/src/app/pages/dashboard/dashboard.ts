import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';


@Component({
  imports: [RouterLink],
  selector: 'app-dashboard',
  styleUrl: './dashboard.scss',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  //private readonly auth = inject(AuthService); ( better user)
 // private readonly progressService = inject(ProgressService);
  //private readonly exerciseService = inject(ExerciseService);
  //readonly progress = this.progressService.progress;
 // readonly activity = this.exerciseService.nextActivity();

  get assessmentCompleted(): boolean {
    // return this.auth.currentUser.assessmentCompleted;
    return true; // Replace with actual logic to check if assessment is completed
  }

  get firstName(): string {
    // return this.auth.currentUser.profile.name.split(/\s+/)[0] || 'there'; ( better user)
    return 'there'; // Replace with actual logic to get the user's
  }
}
