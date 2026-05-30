import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-analyze-result',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatGridListModule,
    MatProgressSpinnerModule,
    NgxChartsModule,
    MatButtonModule
  ],
  templateUrl: './analyze-result.component.html',
  styleUrls: ['./analyze-result.component.scss']
})
export class AnalyzeResultComponent implements OnInit {
  isLoading: boolean = true;
  analysisData: any = null;

  // Options pour les graphiques
  colorScheme = {
    domain: ['#5AA454', '#A10A28', '#C7B42C', '#AAAAAA']
  };

  ngOnInit() {
    // Simuler un chargement
    setTimeout(() => {
      this.loadMockData();
      this.isLoading = false;
    }, 2000);
  }

  loadMockData() {
    this.analysisData = {
      metrics: {
        accuracy: 0.87,
        precision: 0.85,
        recall: 0.89,
        f1Score: 0.87
      },
      featureImportance: [
        { name: 'Age', value: 0.35 },
        { name: 'Revenu', value: 0.28 },
        { name: 'Dépenses', value: 0.20 },
        { name: 'Historique', value: 0.17 }
      ],
      predictions: [
        {
          name: 'Comparaison',
          series: [
            { name: 'Jan', value: 65 },
            { name: 'Fév', value: 59 },
            { name: 'Mar', value: 80 },
            { name: 'Avr', value: 81 },
            { name: 'Mai', value: 56 },
            { name: 'Jun', value: 55 }
          ]
        },
        {
          name: 'Prédictions',
          series: [
            { name: 'Jan', value: 60 },
            { name: 'Fév', value: 55 },
            { name: 'Mar', value: 75 },
            { name: 'Avr', value: 78 },
            { name: 'Mai', value: 52 },
            { name: 'Jun', value: 50 }
          ]
        }
      ],
      confusionMatrix: [
        {
          name: 'Vrai Positif',
          series: [
            { name: 'Prédit Positif', value: 125 },
            { name: 'Prédit Négatif', value: 15 }
          ]
        },
        {
          name: 'Vrai Négatif',
          series: [
            { name: 'Prédit Positif', value: 20 },
            { name: 'Prédit Négatif', value: 140 }
          ]
        }
      ]
    };
  }

  getMetrics() {
    if (!this.analysisData) return [];
    
    return [
      { 
        name: 'Précision', 
        value: this.analysisData.metrics.precision, 
        description: 'Capacité à ne pas classer négatif un résultat positif' 
      },
      { 
        name: 'Rappel', 
        value: this.analysisData.metrics.recall, 
        description: 'Capacité à trouver tous les résultats positifs' 
      },
      { 
        name: 'Exactitude', 
        value: this.analysisData.metrics.accuracy, 
        description: 'Pourcentage de prédictions correctes' 
      },
      { 
        name: 'Score F1', 
        value: this.analysisData.metrics.f1Score, 
        description: 'Moyenne harmonique entre précision et rappel' 
      }
    ];
  }

  generateInterpretation(): string {
    if (!this.analysisData) return '';
    
    let interpretation = 'Basé sur les données de démonstration :\n\n';
    interpretation += '- Le modèle montre une bonne performance globale avec une exactitude de 87%.\n';
    interpretation += '- La caractéristique la plus importante est "Age" avec un score de 35%.\n';
    interpretation += '- Les prédictions suivent bien la tendance des valeurs réelles.\n';
    
    return interpretation;
  }

  reload() {
    this.isLoading = true;
    setTimeout(() => {
      this.loadMockData();
      this.isLoading = false;
    }, 1000);
  }
}