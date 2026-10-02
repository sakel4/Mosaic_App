import {
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Exercise } from '../../../core/models/exercise.model';
import { ExerciseAttempt } from '../../../core/models/exercise-attempt.model';
import { ExerciseMode } from '../../../core/models/exercise-mode.model';
import { UserService } from '../../../core/services/user-service';
import { AssessmentExercise } from '../../../core/models/assessment.model';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';

@Component({
  imports: [],
  selector: 'app-excercise-component',
  styleUrl: './exercise-component.scss',
  templateUrl: './exercise-component.html',
})
export class ExcerciseComponent {
  readonly users = inject(UserService);
  readonly exercise = input.required<Exercise | AssessmentExercise>();
  readonly mode = input.required<ExerciseMode>();
  readonly completed = output<ExerciseAttempt>();
  readonly selected = signal<string | null>(null);
  readonly speakingOption = signal<string | null>(null);
  readonly itemIndex = signal(0);
  readonly itemAnswers = signal<Record<string, string>>({});
  readonly apiExercise = computed(() => {
    const exercise = this.exercise();
    return 'content_data' in exercise ? exercise : null;
  });
  readonly item = computed(() => this.apiExercise()?.content_data.items[this.itemIndex()]);
  readonly content = computed(() => {
    const exercise = this.exercise();
    if ('content' in exercise) return exercise.content;
    const item = this.item();
    return {
      instruction: exercise.instruction,
      prompt: item?.audio_prompt ?? '',
      correctAnswer: item?.correct_option_id ?? '',
    };
  });
  readonly options = computed(() => {
    const exercise = this.exercise();
    return 'content' in exercise
      ? exercise.content.options.map((text) => ({ id: text, text }))
      : (this.item()?.options ?? []);
  });
  readonly hasNextItem = computed(() =>
    this.itemIndex() + 1 < (this.apiExercise()?.content_data.items.length ?? 0),
  );
  readonly promptLines = computed(() => this.content().prompt.split('\n'));
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
    toObservable(this.exercise).pipe(takeUntilDestroyed()).subscribe(() => {
      this.stopSpeech();
      this.itemIndex.set(0);
      this.itemAnswers.set({});
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
    if (answer === null || !this.options().some((option) => option.id === answer)) return;
    const apiExercise = this.apiExercise();
    const item = this.item();
    const answers = item ? { ...this.itemAnswers(), [item.id]: answer } : {};
    if (apiExercise && item && this.hasNextItem()) {
      this.itemAnswers.set(answers);
      this.stopSpeech();
      this.itemIndex.update((index) => index + 1);
      this.selected.set(null);
      this.currentLine.set(0);
      return;
    }
    this.completed.emit({
      exerciseId: this.exercise().id ?? apiExercise!.position,
      answer: apiExercise && apiExercise.content_data.items.length > 1
        ? apiExercise.content_data.items.map((entry) => answers[entry.id]) : answer,
      correct: apiExercise
        ? apiExercise.content_data.items.every((entry) => answers[entry.id] === entry.correct_option_id)
        : answer === this.content().correctAnswer,
      ...(apiExercise ? { itemAnswers: answers } : {}),
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

    const text = [this.content().instruction, this.content().prompt]
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
    this.readText(this.options().find((choice) => choice.id === option)?.text ?? option, option);
  }

  private stopSpeech(): void {
    this.speechRequestId += 1;
    if (this.audioSupported) window.speechSynthesis.cancel();
    this.speechSpeaking.set(false);
    this.speakingOption.set(null);
    this.speechStatus.set('');
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
