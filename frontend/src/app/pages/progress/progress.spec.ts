import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Progress } from './progress';
import { UserService } from '../../core/services/user-service';
import { ProgressService } from '../../core/services/progress-service';
import { createProgressPreview } from '../../core/services/progress-preview';
import { progressEmailDraft } from '../../core/services/progress-report';

describe('Age-appropriate progress', () => {
  const profile = signal({ ageGroup: 'under_12', currentFocus: [] });
  beforeEach(() => {
    profile.set({ ageGroup: 'under_12', currentFocus: [] });
    TestBed.configureTestingModule({
      imports: [Progress],
      providers: [
        provideRouter([]),
        { provide: UserService, useValue: { profile } },
        { provide: ProgressService, useValue: { progress: signal({ ...createProgressPreview(), history: [] }) } },
      ],
    });
  });

  it('shows stars and quests for under-12 learners and keeps detailed charts for older learners', () => {
    const fixture = TestBed.createComponent(Progress);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-kid-progress')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('app-progress-chart')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Level 31');
    expect(fixture.nativeElement.textContent).toContain('Progress report');
    profile.set({ ageGroup: '12_15', currentFocus: [] });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-kid-progress')).toBeNull();
    expect(fixture.nativeElement.querySelector('app-progress-chart')).toBeTruthy();
  });

  it('keeps an email address from injecting extra draft fields', () => {
    const uri = progressEmailDraft('parent+report@example.com&bcc=other@example.com');
    expect(uri).toContain('%26bcc%3D');
    expect(uri).not.toContain('&bcc=');
    expect(decodeURIComponent(uri)).toContain('Attach the downloaded mosaic-progress-sample.pdf before sending.');
  });
});
