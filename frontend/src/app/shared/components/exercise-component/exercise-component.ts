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

interface BrowserRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<{ isFinal: boolean; [index: number]: { transcript: string } }> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionConstructor = new () => BrowserRecognition;

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
  readonly item = computed(() => this.apiExercise()?.content_data.items?.[this.itemIndex()]);
  readonly responseType = computed(() => this.apiExercise()?.response_type ?? 'single_choice_set');
  readonly passage = computed(() => (this.apiExercise()?.content_data.passage ?? []).join('\n'));
  readonly listening = signal(false);
  readonly transcript = signal('');
  readonly recognitionStatus = signal('');
  readonly spokenTarget = computed(() => {
    const data = this.apiExercise()?.content_data;
    return (data?.passage_lines ?? data?.sections?.flatMap((section) => section.items) ?? []).join(' ');
  });
  readonly sequenceStarted = signal(false);
  readonly sequenceVisible = signal<string | null>(null);
  readonly sequenceFinished = signal(false);
  readonly canSubmit = computed(() => {
    if (this.responseType() === 'spoken') return !!this.transcript().trim() && !this.listening();
    if (this.responseType() === 'sequence' && !this.sequenceFinished()) return false;
    return !!this.selected()?.trim();
  });
  readonly content = computed(() => {
    const exercise = this.exercise();
    if ('content' in exercise) return exercise.content;
    const item = this.item();
    return {
      instruction: exercise.instruction,
      prompt: exercise.response_type === 'spoken'
        ? (exercise.content_data.passage_lines ?? exercise.content_data.sections?.flatMap((section) => section.items) ?? []).join('\n')
        : exercise.response_type === 'sequence' ? `Enter the sequence in ${item?.direction ?? 'forward'} order.`
        : exercise.response_type === 'spelling' ? 'Listen to the word, then type its spelling.'
        : item?.prompt ?? item?.audio_prompt ?? item?.grapheme ?? '',
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
    this.itemIndex() + 1 < (this.apiExercise()?.content_data.items?.length ?? 0),
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
  private recognition?: BrowserRecognition;
  private recognitionConstructor(): RecognitionConstructor | undefined {
    if (typeof window === 'undefined') return undefined;
    const browser = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };
    return browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  }
  readonly recognitionSupported = !!this.recognitionConstructor();
  private sequenceTimer?: ReturnType<typeof setTimeout>;
  readonly audioSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  constructor() {
    toObservable(this.exercise).pipe(takeUntilDestroyed()).subscribe(() => {
      this.stopSpeech();
      this.resetRecognition();
      this.resetSequence();
      this.itemIndex.set(0);
      this.itemAnswers.set({});
      this.selected.set(null);
      this.currentLine.set(0);
      this.speakingOption.set(null);
      this.startedAt = Date.now();
    });
    this.destroyRef.onDestroy(() => {
      this.resetRecognition();
      this.resetSequence();
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
    if (!this.canSubmit()) return;
    const answer = this.responseType() === 'spoken' ? this.transcript().trim() : this.selected()!.trim();
    if (this.responseType() === 'single_choice_set' && !this.options().some((option) => option.id === answer)) return;
    const apiExercise = this.apiExercise();
    const item = this.item();
    const answers = item ? { ...this.itemAnswers(), [item.id]: answer } : {};
    if (apiExercise && item && this.hasNextItem()) {
      this.itemAnswers.set(answers);
      this.stopSpeech();
      this.resetSequence();
      this.itemIndex.update((index) => index + 1);
      this.selected.set(null);
      this.currentLine.set(0);
      return;
    }
    const items = apiExercise?.content_data.items ?? [];
    const evaluated = !apiExercise || (this.responseType() === 'spoken' ? !!this.spokenTarget().trim() : (items.length > 0 && items.every((entry) =>
      this.responseType() === 'spelling' ? !!entry.word
      : this.responseType() === 'sequence' ? !!entry.sequence?.length : !!entry.correct_option_id)));
    this.stopSpeech();
    this.completed.emit({
      exerciseId: this.exercise().id ?? apiExercise!.position,
      answer: apiExercise && items.length > 1 ? items.map((entry) => answers[entry.id]) : answer,
      correct: apiExercise ? this.responseType() === 'spoken'
        ? evaluated && this.speechMatches(answer, this.spokenTarget())
        : evaluated && items.every((entry) => {
        if (this.responseType() === 'spelling') return answers[entry.id]?.toLowerCase() === entry.word?.toLowerCase();
        if (this.responseType() === 'sequence') {
          const expected = entry.direction === 'reverse' ? [...entry.sequence!].reverse() : entry.sequence!;
          return this.sequenceTokens(answers[entry.id]).join(',') === expected.join(',');
        }
        return answers[entry.id] === entry.correct_option_id;
      }) : answer === this.content().correctAnswer,
      evaluated,
      ...(apiExercise && this.responseType() !== 'spoken' ? { itemAnswers: this.responseType() === 'sequence'
        ? Object.fromEntries(Object.entries(answers).map(([id, value]) => [id, this.sequenceTokens(value)])) : answers } : {}),
      responseTime: Date.now() - this.startedAt,
      hintsUsed: 0,
    });
  }

  private sequenceTokens(answer: string): string[] {
    return answer.includes(' ') || answer.includes(',') ? answer.split(/[\s,]+/).filter(Boolean) : answer.split('');
  }

  startSequence(): void {
    if (this.sequenceStarted()) return;
    const digits = this.item()?.sequence ?? [];
    this.sequenceStarted.set(true);
    let index = 0;
    const show = () => {
      if (index >= digits.length) {
        this.sequenceVisible.set(null);
        this.sequenceFinished.set(true);
        return;
      }
      this.sequenceVisible.set(digits[index++]);
      this.sequenceTimer = setTimeout(show, this.apiExercise()?.content_data.display_ms_per_digit ?? 900);
    };
    show();
  }

  private resetSequence(): void {
    clearTimeout(this.sequenceTimer);
    this.sequenceStarted.set(false);
    this.sequenceFinished.set(false);
    this.sequenceVisible.set(null);
  }

  private normalizeSpeech(text: string): string {
    return text.normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}\s]/gu, '').replace(/\s+/g, ' ').trim();
  }

  // Word edit distance counts missing, incorrect, and extra words as errors.
  private speechMatches(transcript: string, target: string): boolean {
    const expected = this.normalizeSpeech(target).split(' ').filter(Boolean);
    const actual = this.normalizeSpeech(transcript).split(' ').filter(Boolean);
    if (!expected.length || !actual.length) return false;
    let previous = Array.from({ length: actual.length + 1 }, (_, index) => index);
    for (let i = 1; i <= expected.length; i++) {
      const current = [i];
      for (let j = 1; j <= actual.length; j++) {
        current[j] = Math.min(current[j - 1] + 1, previous[j] + 1,
          previous[j - 1] + (expected[i - 1] === actual[j - 1] ? 0 : 1));
      }
      previous = current;
    }
    return previous[actual.length] * 5 <= expected.length;
  }

  startTranscription(): void {
    if (this.listening()) return;
    const Recognition = this.recognitionConstructor();
    if (!Recognition) {
      this.recognitionStatus.set('Speech recognition is not available in this browser.');
      return;
    }
    this.resetRecognition();
    this.stopSpeech();
    this.transcript.set('');
    this.recognitionStatus.set('');
    const recognition = new Recognition();
    this.recognition = recognition;
    recognition.lang = this.exercise().language ?? navigator.language;
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      if (this.recognition !== recognition) return;
      this.transcript.set(Array.from(event.results).filter((result) => result.isFinal)
        .map((result) => result[0].transcript).join(' '));
    };
    recognition.onerror = (event) => {
      if (this.recognition !== recognition) return;
      this.listening.set(false);
      this.recognitionStatus.set(event.error === 'not-allowed'
        ? 'Allow microphone access to transcribe your reading.' : 'Speech recognition failed. Please try again.');
    };
    recognition.onend = () => {
      if (this.recognition !== recognition) return;
      this.listening.set(false);
      if (!this.recognitionStatus()) this.recognitionStatus.set(this.transcript().trim()
        ? 'Transcription ready. Check your answer or try again.' : 'No speech was recognized. Please try again.');
    };
    try {
      this.listening.set(true);
      recognition.start();
    } catch {
      this.resetRecognition();
      this.recognitionStatus.set('Could not start speech recognition. Please try again.');
    }
  }

  stopTranscription(): void {
    this.recognition?.stop();
  }

  private resetRecognition(): void {
    const recognition = this.recognition;
    this.recognition = undefined;
    recognition?.abort();
    this.listening.set(false);
    this.transcript.set('');
    this.recognitionStatus.set('');
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

    const parts = this.responseType() === 'spelling' ? [this.item()?.word]
      : [this.content().instruction, this.passage(), this.content().prompt];
    const text = parts
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
