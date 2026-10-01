import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Progress } from '../../core/models/progress.model';

@Component({
  selector: 'app-kid-progress',
  imports: [RouterLink],
  templateUrl: './kid-progress.html',
  styleUrl: './kid-progress.scss',
})
export class KidProgress {
  readonly progress = input.required<Progress>();
  readonly level = computed(() => Math.floor(this.progress().exercisesCompleted / 10) + 1);
  readonly levelStars = computed(() => this.progress().exercisesCompleted % 10);
  readonly starsRemaining = computed(() => 10 - this.levelStars());
}
