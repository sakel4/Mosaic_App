import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ProgressWidgets } from './progress-widgets';

describe('ProgressWidgets', () => {
  let component: ProgressWidgets;
  let fixture: ComponentFixture<ProgressWidgets>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProgressWidgets],
    }).compileComponents();

    fixture = TestBed.createComponent(ProgressWidgets);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
