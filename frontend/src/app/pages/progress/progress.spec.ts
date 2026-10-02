import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { Progress } from './progress';
import { UserService } from '../../core/services/user-service';
import { ProgressService } from '../../core/services/progress-service';
import { createProgressPreview } from '../../core/services/progress-preview';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { vi } from 'vitest';

describe('Age-appropriate progress', () => {
  const profile = signal({ ageGroup: 'under_12', currentFocus: [] });
  beforeEach(() => {
    profile.set({ ageGroup: 'under_12', currentFocus: [] });
    TestBed.configureTestingModule({
      imports: [Progress],
      providers: [
        provideRouter([]),
        provideHttpClient(), provideHttpClientTesting(),
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

  it('uploads the PDF and email together and waits for confirmation', async () => {
    const page = TestBed.createComponent(Progress).componentInstance;
    page.email = ' parent@example.com ';
    const pending = page.downloadReport(true);
    const http = TestBed.inject(HttpTestingController);
    const request = await vi.waitFor(() => http.expectOne('/users/progress/email/'));
    expect(page.reportBusy()).toBe(true);
    expect(page.reportStatus()).toBe('');
    expect(request.request.body.get('email')).toBe('parent@example.com');
    expect(request.request.body.get('pdf').type).toBe('application/pdf');
    expect(request.request.headers.has('Content-Type')).toBe(false);
    request.flush({ detail: 'Progress report submitted to the email backend.' });
    await pending;
    expect(page.reportStatus()).toContain('sent to parent@example.com');
    expect(page.reportBusy()).toBe(false);
    http.verify();
  });
});
