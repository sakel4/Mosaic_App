import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';


@Component({
  imports: [RouterLink],
  selector: 'app-dashboard',
  styleUrl: './dashboard.scss',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  //private readonly auth = inject(AuthService);
 // private readonly progressService = inject(ProgressService);
  //private readonly exerciseService = inject(ExerciseService);
  //readonly progress = this.progressService.progress;
 // readonly activity = this.exerciseService.nextActivity();

  get assessmentCompleted(): boolean {
    return true; //this.progressService.assessmentCompleted;
  }

  get firstName(): string {
    return 'John'; // Replace with actual first name retrieval logic
  }
}
