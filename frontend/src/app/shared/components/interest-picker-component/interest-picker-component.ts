import { Component, input, output } from '@angular/core';
import { LearnerInterest } from '../../../core/models/learner-interest.model';

@Component({
  imports: [],
  selector: 'app-interest-picker-component',
  styleUrl: './interest-picker-component.scss',
  templateUrl: './interest-picker-component.html',
})
export class InterestPickerComponent {
  readonly options = input.required<readonly LearnerInterest[]>();
  readonly selected = input.required<LearnerInterest[]>();
  readonly selectedChange = output<LearnerInterest[]>();

  toggle(interest: LearnerInterest): void {
    const selected = this.selected();
    this.selectedChange.emit(
      selected.includes(interest)
        ? selected.filter((item) => item !== interest)
        : [...selected, interest],
    );
  }
}
