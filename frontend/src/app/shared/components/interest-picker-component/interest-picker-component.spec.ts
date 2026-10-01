import { ComponentFixture, TestBed } from '@angular/core/testing';
import { InterestPickerComponent } from './interest-picker-component';

describe('InterestPickerComponent', () => {
  let component: InterestPickerComponent;
  let fixture: ComponentFixture<InterestPickerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [InterestPickerComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(InterestPickerComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
