import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgxChartsModule } from '@swimlane/ngx-charts';

@Component({
  selector: 'app-analyze-result',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatGridListModule,
    MatProgressSpinnerModule,
    NgxChartsModule
  ],
  templateUrl: './analyze-result.component.html',
  styleUrls: ['./analyze-result.component.scss']
})
export class AnalyzeResultComponent {
  @Input() isLoading: boolean = false;
  @Input() analysisData: AnalysisData | null = null;

  // Options pour les graphiques
  colorScheme = {
    domain: ['#5AA454', '#A10A28', '#C7B42C', '#AAAAAA']
  };
}

interface AnalysisData {
  metrics: {
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1Score?: number;
  };
  featureImportance: { name: string; value: number }[];
  predictions: { name: string; series: { name: string; value: number }[] }[];
  confusionMatrix: { name: string; series: { name: string; value: number }[] }[];
  timeSeries?: { name: string; series: { name: string; value: number }[] }[];
}