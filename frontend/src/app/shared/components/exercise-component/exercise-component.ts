import {
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Exercise } from '../../../core/models/exercise.model';
import { ExerciseAttempt } from '../../../core/models/exercise-attempt.model';
import { ExerciseMode } from '../../../core/models/exercise-mode.model';
import { UserService } from '../../../core/services/user-service';

@Component({
  imports: [],
  selector: 'app-excercise-component',
  styleUrl: './exercise-component.scss',
  templateUrl: './exercise-component.html',
})
export class ExcerciseComponent {
  readonly users = inject(UserService);
  readonly exercise = input.required<Exercise>();
  readonly mode = input.required<ExerciseMode>();
  readonly completed = output<ExerciseAttempt>();
  readonly selected = signal<string | null>(null);
  readonly speakingOption = signal<string | null>(null);
  readonly promptLines = computed(() => this.exercise().content.prompt.split('\n'));
  readonly currentLine = signal(0);
  readonly promptFontSize = computed(() => {
    const sizes = { comfortable: '24px', large: '30px', 'extra-large': '36px' };
    return sizes[this.users.fontSize()];
  });
  readonly choiceFontSize = computed(() => {
    const sizes = { comfortable: '14px', large: '18px', 'extra-large': '22px' };
    return sizes[this.users.fontSize()];
  });
  readonly supportFontSize = computed(() => {
    const sizes = { comfortable: '11px', large: '13px', 'extra-large': '15px' };
    return sizes[this.users.fontSize()];
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
    this.currentLine.update((line) =>
      Math.max(0, Math.min(this.promptLines().length - 1, line + direction)),
    );
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
      if (
        requestId !== this.speechRequestId ||
        event.error === 'canceled' ||
        event.error === 'interrupted'
      )
        return;
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