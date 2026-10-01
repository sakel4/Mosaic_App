import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RealWorld } from './real-world';

describe('RealWorld', () => {
  let component: RealWorld;
  let fixture: ComponentFixture<RealWorld>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealWorld],
    }).compileComponents();

    fixture = TestBed.createComponent(RealWorld);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
