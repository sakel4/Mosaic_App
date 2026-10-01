
import { Component, computed, DestroyRef, effect, inject, input, output, signal } from '@angular/core';
import { Exercise } from '../../../core/models/exercise.model';
import { ExerciseAttempt } from '../../../core/models/exercise-attempt.model';
import { ExerciseMode } from '../../../core/models/exercise-mode.model';
// import { UserService } from '../core/services/onoma.services';

@Component({
  imports: [],
  selector: 'app-excercise-component',
  styleUrl: './exercise-component.scss',
  templateUrl: './exercise-component.html',
})
export class ExcerciseComponent {
  //readonly users = inject(UserService);
  readonly exercise = input.required<Exercise>();
  readonly mode = input.required<ExerciseMode>();
  readonly completed = output<ExerciseAttempt>();
  readonly selected = signal<string | null>(null);
  readonly speakingOption = signal<string | null>(null);
  readonly promptLines = computed(() => this.exercise().content.prompt.split('\n'));
  readonly currentLine = signal(0);
  readonly promptFontSize = computed(() => {
    const sizes = { comfortable: '24px', large: '30px', 'extra-large': '36px' };
    // return sizes[this.users.fontSize()];
    return sizes['comfortable'];
  });
  readonly choiceFontSize = computed(() => {
    const sizes = { comfortable: '14px', large: '18px', 'extra-large': '22px' };
    // return sizes[this.users.fontSize()];
    return sizes['comfortable'];  
  });
  readonly supportFontSize = computed(() => {
    const sizes = { comfortable: '11px', large: '13px', 'extra-large': '15px' };
    // return sizes[this.users.fontSize()];
  });
  readonly speechSpeaking = signal(false);
  readonly speechStatus = signal('');
  private readonly destroyRef = inject(DestroyRef);
  private speechRequestId = 0;
  private startedAt = Date.now();
  readonly audioSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  constructor() {
    effect(() => {
      this.exercise().id;
      this.selected.set(null);
      this.currentLine.set(0);
      this.speakingOption.set(null);
      this.startedAt = Date.now();
    });
    this.destroyRef.onDestroy(() => {
      if (this.audioSupported) window.speechSynthesis?.cancel();
    });
  }

  choose(answer: string): void {
    this.selected.set(answer);
  }

  moveLine(direction: -1 | 1): void {
    this.currentLine.update((line) => Math.max(0, Math.min(this.promptLines().length - 1, line + direction)));
  }

  submit(): void {
    const answer = this.selected();
    if (!answer) return;
    this.completed.emit({
      exerciseId: this.exercise().id,
      answer,
      correct: answer === this.exercise().content.correctAnswer,
      responseTime: Date.now() - this.startedAt,
      hintsUsed: 0,
    });
  }

  readPrompt(): void {
    if (this.speechSpeaking()) {
      this.speechRequestId += 1;
      window.speechSynthesis.cancel();
      this.speechSpeaking.set(false);
      this.speakingOption.set(null);
      this.speechStatus.set('Speech stopped.');
      return;
    }

    const text = [this.exercise().content.instruction, this.exercise().content.prompt]
      .filter((part): part is string => Boolean(part?.trim()))
      .join(' ');
    this.readText(text);
  }

  readChoice(option: string): void {
    if (this.speakingOption() === option && this.speechSpeaking()) {
      this.speechRequestId += 1;
      window.speechSynthesis.cancel();
      this.speechSpeaking.set(false);
      this.speakingOption.set(null);
      this.speechStatus.set('Speech stopped.');
      return;
    }
    this.readText(option, option);
  }

  private readText(text: string, option: string | null = null): void {
    if (!this.audioSupported) {
      this.speechStatus.set('Speech playback is not available in this browser.');
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    const requestId = ++this.speechRequestId;
    utterance.lang = this.exercise().language ?? navigator.language;
    utterance.rate = 0.9;
    utterance.onstart = () => {
      if (requestId !== this.speechRequestId) return;
      this.speechSpeaking.set(true);
      this.speakingOption.set(option);
      this.speechStatus.set('');
    };
    utterance.onend = () => {
      if (requestId !== this.speechRequestId) return;
      this.speechSpeaking.set(false);
      this.speakingOption.set(null);
    };
    utterance.onerror = (event) => {
      if (requestId !== this.speechRequestId || event.error === 'canceled' || event.error === 'interrupted') return;
      this.speechSpeaking.set(false);
      this.speakingOption.set(null);
      this.speechStatus.set('Speech playback failed. Please try again.');
    };

    this.speechStatus.set('');
    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      this.speechSpeaking.set(true);
      this.speakingOption.set(option);
    } catch {
      this.speechSpeaking.set(false);
      this.speakingOption.set(null);
      this.speechStatus.set('Speech playback failed. Please try again.');
    }
  }
}

@Component({
  selector: 'app-exercise-feedback',
  template: `
    <section class="feedback-card" [class.encouraging]="attempt().correct" aria-live="polite">
      <span class="feedback-icon" aria-hidden="true">{{ attempt().correct ? '✓' : '↗' }}</span>
      <div class="feedback-copy">
        <h2>{{ attempt().correct ? 'Nice work!' : 'Not quite — keep exploring' }}</h2>
        <p>{{ attempt().correct ? exercise().content.explanation : 'The answer was “' + exercise().content.correctAnswer + '”. ' + exercise().content.explanation }}</p>
      </div>
      <button class="primary-button" type="button" (click)="continued.emit()">
        {{ continueLabel() }} <span aria-hidden="true">→</span>
      </button>
    </section>
  `,
  styles: [`
    .feedback-card { display: flex; align-items: center; gap: 15px; padding: 20px; border: 1px solid var(--feedback-border);
      border-radius: 16px; background: var(--feedback-surface); }
    .feedback-card.encouraging { border-color: var(--feedback-positive-border); background: var(--feedback-positive-surface); }
    .feedback-icon { display: grid; width: 39px; height: 39px; flex: 0 0 auto; place-items: center;
      border-radius: 13px; background: var(--mosaic-coral); color: var(--mosaic-rose); font-size: 17px; font-weight: 700; }
    .encouraging .feedback-icon { background: var(--feedback-positive-border); color: var(--feedback-positive-icon); }
    .feedback-copy { flex: 1; }
    h2 { margin: 0 0 3px; font: 700 15px 'Manrope', sans-serif; }
    p { margin: 0; color: var(--muted); font-size: 12px; }
    .feedback-card .primary-button { min-height: 41px; padding-inline: 15px; background: var(--primary-action); font-size: 12px; }
    .feedback-card .primary-button:hover { background: var(--primary-action-hover); }
    @media (max-width: 640px) {
      .feedback-card { align-items: flex-start; flex-wrap: wrap; padding: 15px; }
      .feedback-copy { min-width: calc(100% - 58px); }
      .feedback-card .primary-button { width: 100%; }
    }
  `],
})
export class ExerciseFeedbackComponent {
  readonly attempt = input.required<ExerciseAttempt>();
  readonly exercise = input.required<Exercise>();
  readonly continueLabel = input('Continue');
  readonly continued = output<void>();
}
