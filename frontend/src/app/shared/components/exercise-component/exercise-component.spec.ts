import { vi } from 'vitest';
import suppliedFixture from '../../../core/data/assessment-under-12.json';
import { exercises } from '../../../core/services/dummy_data';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExcerciseComponent } from './exercise-component';
import { provideHttpClient } from '@angular/common/http';
import { AssessmentExercise, assessmentExercises } from '../../../core/models/assessment.model';

describe('ExcerciseComponent', () => {
  let component: ExcerciseComponent;
  let fixture: ComponentFixture<ExcerciseComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExcerciseComponent],
      providers: [provideHttpClient()],
    }).compileComponents();

    fixture = TestBed.createComponent(ExcerciseComponent);
    fixture.componentRef.setInput('exercise', exercises[0]);
    fixture.componentRef.setInput('mode', 'practice');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('renders API option labels and emits IDs for every item', async () => {
    const exercise: AssessmentExercise = {
      position: 1, kind: 'phoneme_manipulation', skill: 'phonological_awareness',
      difficulty: 3, response_type: 'single_choice_set', instruction: 'Listen and choose.',
      content_data: { items: [
        { id: 'a', audio_prompt: 'Remove /s/ from smile.', options: [{ id: '1', text: 'mile' }], correct_option_id: '1' },
        { id: 'b', audio_prompt: 'Remove /p/ from plane.', options: [{ id: '2', text: 'lane' }], correct_option_id: '2' },
      ] },
    };
    fixture.componentRef.setInput('exercise', exercise);
    await fixture.whenStable();
    const attempts: unknown[] = [];
    component.completed.subscribe((attempt) => attempts.push(attempt));
    expect(fixture.nativeElement.textContent).toContain('mile');
    component.choose('1');
    component.submit();
    expect(attempts).toHaveLength(0);
    expect(component.content().prompt).toContain('plane');
    expect(component.selected()).toBeNull();
    component.choose('2');
    component.submit();
    expect(attempts[0]).toMatchObject({ exerciseId: 1, answer: ['1', '2'], correct: true, itemAnswers: { a: '1', b: '2' } });
  });

  it('inherits the language from the REST envelope with the supplied excercises spelling', () => {
    const exercises = assessmentExercises({ assessment: {
      age_group: '12_15', language: 'en', estimated_duration_seconds: 72, type: 'assessment',
      excercises: [{ position: 1, kind: 'phoneme_manipulation', skill: 'phonological_awareness', difficulty: 3,
        response_type: 'single_choice_set', instruction: 'Listen.', content_data: { items: [] } }],
    } });
    expect(exercises[0].language).toBe('en');
  });
  async function loadSupplied(index: number) {
    const activities = assessmentExercises(suppliedFixture as Parameters<typeof assessmentExercises>[0]);
    fixture.componentRef.setInput('exercise', activities[index]);
    fixture.componentRef.setInput('mode', 'assessment');
    await fixture.whenStable();
  }

  it('renders graphemes and leaves answers without a key unevaluated', async () => {
    await loadSupplied(1);
    expect(component.content().prompt).toBe('m');
    const emitted = vi.fn();
    component.completed.subscribe(emitted);
    component.choose('1');
    component.submit();
    expect(emitted).toHaveBeenCalledWith(expect.objectContaining({
      exerciseId: suppliedFixture[0].excercises[1].id, evaluated: false, itemAnswers: { a: '1' },
    }));
  });

  it('renders both spoken content shapes without requiring items', async () => {
    await loadSupplied(2);
    expect(fixture.nativeElement.textContent).not.toContain('Made-up words');
    expect(fixture.nativeElement.textContent).not.toContain('Real words');
    expect(fixture.nativeElement.textContent).toContain('froat');
    expect(component.canSubmit()).toBe(false);
    await loadSupplied(3);
    expect(fixture.nativeElement.textContent).toContain('Maya found a small box');
    expect(fixture.nativeElement.textContent).toContain('Speech recognition is not available');
  });

  it('accepts typed spelling without exposing the dictated word', async () => {
    await loadSupplied(4);
    expect(fixture.nativeElement.querySelector('input')).toBeTruthy();
    expect(fixture.nativeElement.textContent).not.toContain('ship');
    const emitted = vi.fn();
    component.completed.subscribe(emitted);
    component.choose('ship');
    component.submit();
    expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ correct: true, itemAnswers: { a: 'ship' } }));
  });

  it('supports typed_text spelling through the Listen button and typed input', async () => {
    const speak = vi.fn();
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak });
    vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} });
    const spellingFixture = TestBed.createComponent(ExcerciseComponent);
    try {
      spellingFixture.componentRef.setInput('exercise', {
        id: 'spelling', position: 1, kind: 'spelling', skill: 'spelling', response_type: 'typed_text',
        instruction: 'Listen to each dictated word and type it. You do not need to speak.',
        content_data: { items: [{ id: 'a', word: 'ship', sentence: 'The ship crossed the water.' }] },
      });
      spellingFixture.componentRef.setInput('mode', 'assessment');
      await spellingFixture.whenStable();
      spellingFixture.nativeElement.querySelector('.audio-button').click();
      expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: 'ship' }));
      const input = spellingFixture.nativeElement.querySelector('input');
      expect(input).toBeTruthy();
      input.value = 'Ship';
      input.dispatchEvent(new Event('input'));
      spellingFixture.detectChanges();
      const emitted = vi.fn();
      spellingFixture.componentInstance.completed.subscribe(emitted);
      const submit = spellingFixture.nativeElement.querySelector('.exercise-actions .primary-button');
      expect(submit.disabled).toBe(false);
      submit.click();
      expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ correct: true, itemAnswers: { a: 'Ship' } }));
    } finally {
      spellingFixture.destroy();
      vi.unstubAllGlobals();
    }
  });

  it('shows the comprehension passage and question', async () => {
    await loadSupplied(5);
    expect(fixture.nativeElement.textContent).toContain('Leo was getting ready');
    expect(fixture.nativeElement.textContent).toContain('Why did Leo take an umbrella?');
  });

  it('hides the timed sequence before accepting its reverse', async () => {
    await loadSupplied(6);
    vi.useFakeTimers();
    try {
      component.startSequence();
      expect(component.sequenceVisible()).toBe('4');
      component.choose('7 1 4');
      expect(component.canSubmit()).toBe(false);
      vi.advanceTimersByTime(2700);
      expect(component.sequenceVisible()).toBeNull();
      expect(component.canSubmit()).toBe(true);
      const emitted = vi.fn();
      component.completed.subscribe(emitted);
      component.submit();
      expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ correct: true }));
    } finally { vi.useRealTimers(); }
  });

  it('transcribes reading and matches text regardless of punctuation, case, or line breaks', async () => {
    await loadSupplied(3);
    let recognition: any;
    class RecognitionMock {
      lang = '';
      continuous = false;
      interimResults = false;
      onresult: any;
      onend: any;
      onerror: any;
      constructor() { recognition = this; }
      start() {}
      stop() { this.onend(); }
      abort = vi.fn();
    }
    vi.stubGlobal('SpeechRecognition', RecognitionMock);
    try {
      component.startTranscription();
      expect(component.listening()).toBe(true);
      expect(recognition.lang).toBe('en');
      const text = component.spokenTarget().toUpperCase().replace(/[.,]/g, '');
      recognition.onresult({ results: [{ isFinal: true, 0: { transcript: text } }] });
      expect(component.canSubmit()).toBe(false);
      component.stopTranscription();
      expect(component.canSubmit()).toBe(true);
      const emitted = vi.fn();
      component.completed.subscribe(emitted);
      component.submit();
      expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ evaluated: true, correct: true, answer: text }));
      expect(emitted.mock.calls[0][0]).not.toHaveProperty('audio');
    } finally { vi.unstubAllGlobals(); }
  });

  it('marks an incomplete spoken passage incorrect', async () => {
    await loadSupplied(3);
    component.transcript.set('Maya found a small box');
    const emitted = vi.fn();
    component.completed.subscribe(emitted);
    component.submit();
    expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ evaluated: true, correct: false }));
  });

  it('matches spoken section words without requiring the section label', async () => {
    await loadSupplied(2);
    component.transcript.set('lat mip shen plim froat');
    const emitted = vi.fn();
    component.completed.subscribe(emitted);
    component.submit();
    expect(emitted).toHaveBeenCalledWith(expect.objectContaining({ evaluated: true, correct: true }));
  });

  it('accepts 80% word accuracy but rejects less than 80% and excessive extra words', async () => {
    await loadSupplied(2);
    const emitted = vi.fn();
    component.completed.subscribe(emitted);
    component.transcript.set('lat mip shen plim wrong');
    component.submit();
    expect(emitted.mock.lastCall![0].correct).toBe(true);
    component.transcript.set('lat mip shen wrong wrong');
    component.submit();
    expect(emitted.mock.lastCall![0].correct).toBe(false);
    component.transcript.set('lat mip shen plim froat extra extra');
    component.submit();
    expect(emitted.mock.lastCall![0].correct).toBe(false);
  });

  it('offers speech playback for choices even when the preference is disabled', async () => {
    const speak = vi.fn();
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak });
    vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} });
    try {
      const audioFixture = TestBed.createComponent(ExcerciseComponent);
      audioFixture.componentRef.setInput('exercise', exercises[0]);
      audioFixture.componentRef.setInput('mode', 'practice');
      const audioComponent = audioFixture.componentInstance;
      const profile = audioComponent.users.profile();
      vi.spyOn(audioComponent.users, 'profile').mockReturnValue({ ...profile, preferences: { ...profile.preferences, textToSpeech: false } });
      await audioFixture.whenStable();
      const button = audioFixture.nativeElement.querySelector('.choice-audio-button');
      expect(button).toBeTruthy();
      button.click();
      expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: exercises[0].content.options[0] }));
      expect(audioComponent.selected()).toBeNull();
      audioFixture.destroy();
    } finally { vi.unstubAllGlobals(); }
  });
});
