import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { UserService } from '../../core/services/user-service';
import { ExerciseService } from '../../core/services/exercise-service';
import { ProgressService } from '../../core/services/progress-service';
import { computed } from '@angular/core';
import { DatePipe, UpperCasePipe } from '@angular/common'

@Component({
  imports: [RouterLink, DatePipe, UpperCasePipe],
  selector: 'app-dashboard',
  styleUrl: './dashboard.scss',
  templateUrl: './dashboard.html',
})
export class Dashboard {
  private readonly users = inject(UserService);
  private readonly progressService = inject(ProgressService);
  private readonly exerciseService = inject(ExerciseService);
  readonly progress = this.progressService.progress;
  readonly activity = this.exerciseService.nextActivity();
  readonly isChild = computed(() => this.users.profile().ageGroup === 'under_12');
  readonly level = computed(() => Math.floor(this.progress().exercisesCompleted / 10) + 1);
  readonly levelStars = computed(() => this.progress().exercisesCompleted % 10);

  currentDate = new Date();

  get assessmentCompleted(): boolean {
    return this.users.assessmentCompleted();
  }
  get firstName(): string {
    return this.users.profile().name.trim().split(/\s+/)[0] || 'there';
  }
}
