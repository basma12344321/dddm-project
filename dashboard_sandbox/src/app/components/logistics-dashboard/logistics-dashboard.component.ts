import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgApexchartsModule } from 'ng-apexcharts';
import {
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexYAxis,
  ApexTooltip,
  ApexDataLabels,
  ApexPlotOptions,
  ApexLegend,
  ApexGrid,
  ApexTitleSubtitle,
  ApexFill,
  ApexStroke
} from 'ng-apexcharts';

export interface LogisticsMetrics {
  makespan: number;
  machine_utilization: { [key: string]: number };
  balance_index: number;
  on_time_rate: number;
  total_tardiness: number;
  average_setup_overhead: number;
  critical_path_length: number;
}

export interface ConvergencePoint {
  iteration: number;
  temperature: number;
  current_score: number;
  best_score: number;
}

export interface OptimizationGain {
  initial_makespan: number;
  optimized_makespan: number;
  makespan_reduction_pct: number;
  balance_improvement: number;
  tardiness_reduction_pct: number;
}

export interface InterpretationData {
  performance_level: string;
  summary: string;
  recommendations: string[];
  warnings: string[];
}

@Component({
  selector: 'app-logistics-dashboard',
  standalone: true,
  imports: [CommonModule, NgApexchartsModule],
  template: `
    <div class="dashboard-container">
      <!-- Métriques principales -->
      <div class="metrics-cards">
        <div class="metric-card">
          <div class="metric-icon makespan">
            <i class="material-icons">schedule</i>
          </div>
          <div class="metric-content">
            <span class="metric-label">Makespan Total</span>
            <span class="metric-value">{{metrics?.makespan || 0}}</span>
            <span class="metric-unit">unités</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon ontime">
            <i class="material-icons">check_circle</i>
          </div>
          <div class="metric-content">
            <span class="metric-label">Taux de conformité</span>
            <span class="metric-value">{{((metrics?.on_time_rate || 0) * 100).toFixed(0)}}%</span>
            <span class="metric-unit">dans les temps</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon balance">
            <i class="material-icons">balance</i>
          </div>
          <div class="metric-content">
            <span class="metric-label">Index d'équilibrage</span>
            <span class="metric-value">{{(metrics?.balance_index || 0).toFixed(2)}}</span>
            <span class="metric-unit">/ 1.0</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon utilization">
            <i class="material-icons">memory</i>
          </div>
          <div class="metric-content">
            <span class="metric-label">Utilisation moy.</span>
            <span class="metric-value">{{averageUtilization}}%</span>
            <span class="metric-unit">machines</span>
          </div>
        </div>
      </div>

      <!-- Graphiques -->
      <div class="charts-grid">
        <!-- Utilisation des machines -->
        <div class="chart-card">
          <h4>Utilisation des Machines</h4>
          <div id="machine-utilization-chart" *ngIf="utilizationChartOptions">
            <apx-chart
              [series]="utilizationChartOptions.series"
              [chart]="utilizationChartOptions.chart"
              [plotOptions]="utilizationChartOptions.plotOptions"
              [colors]="utilizationChartOptions.colors"
              [xaxis]="utilizationChartOptions.xaxis"
              [yaxis]="utilizationChartOptions.yaxis"
              [grid]="utilizationChartOptions.grid"
              [tooltip]="utilizationChartOptions.tooltip"
            ></apx-chart>
          </div>
        </div>

        <!-- Convergence du Recuit Simulé -->
        <div class="chart-card" *ngIf="convergenceData && convergenceData.length > 0">
          <h4>Convergence - Recuit Simulé</h4>
          <div id="convergence-chart" *ngIf="convergenceChartOptions">
            <apx-chart
              [series]="convergenceChartOptions.series"
              [chart]="convergenceChartOptions.chart"
              [colors]="convergenceChartOptions.colors"
              [xaxis]="convergenceChartOptions.xaxis"
              [yaxis]="convergenceChartOptions.yaxis"
              [grid]="convergenceChartOptions.grid"
              [legend]="convergenceChartOptions.legend"
              [tooltip]="convergenceChartOptions.tooltip"
            ></apx-chart>
          </div>
        </div>
      </div>

      <!-- Optimisation Gain -->
      <div class="optimization-section" *ngIf="optimizationGain">
        <h4>📈 Gain d'Optimisation</h4>
        <div class="gain-cards">
          <div class="gain-card" *ngIf="optimizationGain.makespan_reduction_pct">
            <span class="gain-label">Makespan</span>
            <span class="gain-value positive">-{{optimizationGain.makespan_reduction_pct}}%</span>
            <span class="gain-detail">{{optimizationGain.initial_makespan}} → {{optimizationGain.optimized_makespan}}</span>
          </div>
          <div class="gain-card" *ngIf="optimizationGain.balance_improvement">
            <span class="gain-label">Équilibrage</span>
            <span class="gain-value positive">+{{(optimizationGain.balance_improvement * 100).toFixed(1)}}%</span>
          </div>
          <div class="gain-card" *ngIf="optimizationGain.tardiness_reduction_pct">
            <span class="gain-label">Retard</span>
            <span class="gain-value positive">-{{optimizationGain.tardiness_reduction_pct}}%</span>
          </div>
        </div>
      </div>

      <!-- Interprétation et Recommandations -->
      <div class="interpretation-section" *ngIf="interpretation">
        <h4>💡 Interprétation</h4>
        <div class="performance-badge" [class]="interpretation.performance_level.toLowerCase()">
          {{interpretation.performance_level}}
        </div>
        <p class="summary-text">{{interpretation.summary}}</p>

        <!-- Recommandations -->
        <div class="recommendations" *ngIf="interpretation.recommendations?.length > 0">
          <h5>Recommandations</h5>
          <ul>
            <li *ngFor="let rec of interpretation.recommendations">
              <i class="material-icons">lightbulb</i> {{rec}}
            </li>
          </ul>
        </div>

        <!-- Warnings -->
        <div class="warnings" *ngIf="interpretation.warnings?.length > 0">
          <h5>Alertes</h5>
          <ul>
            <li *ngFor="let warning of interpretation.warnings" class="warning-item">
              <i class="material-icons">warning</i> {{warning}}
            </li>
          </ul>
        </div>
      </div>

      <div class="interpretation-ia-section" *ngIf="interpretationIa">
        <h4> Analyse IA</h4>
        <div class="ia-content" [innerHTML]="formattedIa"></div>
      </div>

      <!-- Temps d'exécution -->
      <div class="execution-time" *ngIf="executionTimeMs">
        <span>Temps d'exécution: {{executionTimeMs}} ms</span>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      padding: 20px;
    }

    /* Métriques Cards - 4 sur la même ligne */
    .metrics-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr); /* Force 4 colonnes de taille égale */
      gap: 20px;
      margin-bottom: 30px;
    }

    /* Sécurité : Si tu réduis beaucoup la fenêtre de ton PC ou sur tablette */
    @media (max-width: 1024px) {
      .metrics-cards {
        grid-template-columns: repeat(2, 1fr); /* Passe à 2 en haut, 2 en bas pour que ce soit beau */
      }
    }

    /* Sécurité : Sur téléphone */
    @media (max-width: 600px) {
      .metrics-cards {
        grid-template-columns: 1fr; /* 1 par ligne */
      }
    }

    .metric-card {
      display: flex;
      align-items: center;
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      transition: transform 0.2s;
    }

    .metric-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 15px rgba(0,0,0,0.12);
    }

    .metric-icon {
      width: 50px;
      height: 50px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 15px;
    }

    .metric-icon i {
      font-size: 24px;
      color: white;
    }

    .metric-icon.makespan { background: linear-gradient(135deg, #667eea, #764ba2); }
    .metric-icon.ontime { background: linear-gradient(135deg, #4caf50, #2e7d32); }
    .metric-icon.balance { background: linear-gradient(135deg, #ff9800, #f57c00); }
    .metric-icon.utilization { background: linear-gradient(135deg, #2196f3, #1976d2); }

    .metric-content {
      display: flex;
      flex-direction: column;
    }

    .metric-label {
      font-size: 12px;
      color: #666;
      text-transform: uppercase;
    }

    .metric-value {
      font-size: 28px;
      font-weight: 700;
      color: #333;
      line-height: 1.2;
    }

    .metric-unit {
      font-size: 11px;
      color: #999;
    }

    /* Graphiques */
    .charts-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 30px;
    }

    .chart-card {
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }

    .chart-card h4 {
      margin: 0 0 15px 0;
      color: #333;
      font-weight: 600;
    }

    /* Optimisation */
    .optimization-section {
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 30px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }

    .optimization-section h4 {
      margin: 0 0 15px 0;
      color: #333;
    }

    .gain-cards {
      display: flex;
      gap: 15px;
    }

    .gain-card {
      flex: 1;
      background: #f8f9fa;
      border-radius: 8px;
      padding: 15px;
      text-align: center;
    }

    .gain-label {
      display: block;
      font-size: 12px;
      color: #666;
      text-transform: uppercase;
      margin-bottom: 5px;
    }

    .gain-value {
      display: block;
      font-size: 24px;
      font-weight: 700;
    }

    .gain-value.positive { color: #4caf50; }
    .gain-value.negative { color: #f44336; }

    .gain-detail {
      display: block;
      font-size: 11px;
      color: #999;
      margin-top: 5px;
    }

    /* Interprétation */
    .interpretation-section {
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 30px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }

    .interpretation-section h4 {
      margin: 0 0 15px 0;
      color: #333;
    }

    .performance-badge {
      display: inline-block;
      padding: 8px 20px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 14px;
      margin-bottom: 15px;
    }

    .performance-badge.excellent { background: #4caf50; color: white; }
    .performance-badge.bon { background: #2196f3; color: white; }
    .performance-badge.moyen { background: #ff9800; color: white; }
    .performance-badge.critique { background: #f44336; color: white; }

    .summary-text {
      color: #555;
      line-height: 1.6;
      margin-bottom: 20px;
    }

    .recommendations, .warnings {
      margin-top: 15px;
    }

    .recommendations h5, .warnings h5 {
      margin: 0 0 10px 0;
      color: #333;
      font-size: 14px;
    }

    .recommendations ul, .warnings ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .recommendations li {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      background: #e8f5e9;
      border-radius: 6px;
      margin-bottom: 8px;
      color: #2e7d32;
    }

    .recommendations li i {
      color: #4caf50;
      font-size: 18px;
    }

    .warnings li {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      background: #fff3e0;
      border-radius: 6px;
      margin-bottom: 8px;
      color: #e65100;
    }

    .warnings li i {
      color: #ff9800;
      font-size: 18px;
    }

    /* Execution time */
    .execution-time {
      text-align: right;
      color: #999;
      font-size: 12px;
    }

    .interpretation-ia-section {
      background: linear-gradient(135deg, #fff8f0 0%, #fff 100%);
      border: 1px solid rgba(255, 71, 87, 0.12);
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 30px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    }
    .interpretation-ia-section h4 { margin: 0 0 15px 0; color: #ff4757; font-weight: 600; }
    .ia-content { color: #444; line-height: 1.75; font-size: 14px; }
    .ia-content strong { color: #222; font-weight: 700; }

    @media (max-width: 768px) {
      .metrics-cards {
        grid-template-columns: repeat(2, 1fr);
      }

      .charts-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class LogisticsDashboardComponent implements OnChanges {
  @Input() metrics: LogisticsMetrics | null = null;
  @Input() convergenceData: ConvergencePoint[] = [];
  @Input() optimizationGain: OptimizationGain | null = null;
  @Input() interpretation: InterpretationData | null = null;
  @Input() executionTimeMs: number = 0;
  @Input() interpretationIa: string = '';

  utilizationChartOptions: any;
  convergenceChartOptions: any;

  get averageUtilization(): number {
    if (!this.metrics?.machine_utilization) return 0;
    const utils = Object.values(this.metrics.machine_utilization);
    return utils.length > 0
      ? (utils.reduce((a, b) => a + b, 0) / utils.length * 100).toFixed(0) as any
      : 0;
  }

  get formattedIa(): string {
    if (!this.interpretationIa) return '';
    return this.interpretationIa
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['metrics'] && this.metrics) {
      this.updateUtilizationChart();
    }
    if (changes['convergenceData'] && this.convergenceData.length > 0) {
      this.updateConvergenceChart();
    }
  }

  updateUtilizationChart(): void {
    if (!this.metrics?.machine_utilization) return;

    const machines = Object.keys(this.metrics.machine_utilization);
    const utilization = Object.values(this.metrics.machine_utilization).map(v => (v * 100).toFixed(0));
    const avg = this.averageUtilization;

    this.utilizationChartOptions = {
      series: [{
        name: 'Utilisation',
        data: utilization.map(u => parseInt(u))
      }],
      chart: {
        type: 'bar',
        height: 250,
        toolbar: { show: false }
      },
      plotOptions: {
        bar: {
          horizontal: true,
          borderRadius: 4,
          distributed: true,
          dataLabels: {
            position: 'top'
          }
        }
      },
      colors: utilization.map(u => {
        const val = parseInt(u);
        if (val < 70) return '#4caf50';
        if (val < 90) return '#ff9800';
        return '#f44336';
      }),
      xaxis: {
        max: 100,
        labels: {
          style: { fontSize: '11px' }
        },
        title: {
          text: 'Pourcentage (%)'
        }
      },
      yaxis: {
        labels: {
          style: { fontSize: '12px', fontWeight: 600 }
        }
      },
      grid: {
        show: true,
        borderColor: '#f1f1f1'
      },
      tooltip: {
        custom: ({ dataPointIndex }: { dataPointIndex: number }) => {
          const val = utilization[dataPointIndex];
          return `<div class="apex-tooltip">${machines[dataPointIndex]}: ${val}%</div>`;
        }
      },
      dataLabels: {
        enabled: true,
        formatter: (val: number | string) => val + '%',
        style: {
          fontSize: '11px',
          colors: ['#fff']
        }
      }
    };

    // Ajouter ligne de moyenne
    setTimeout(() => {
      const chart = document.querySelector('#machine-utilization-chart apx-chart');
      if (chart) {
        // La ligne de référence sera ajoutée via les options de grille
      }
    }, 100);
  }

  updateConvergenceChart(): void {
    if (this.convergenceData.length === 0) return;

    const iterations = this.convergenceData.map(c => c.iteration);
    const currentScores = this.convergenceData.map(c => c.current_score);
    const bestScores = this.convergenceData.map(c => c.best_score);

    this.convergenceChartOptions = {
      series: [
        {
          name: 'Score Courant',
          data: currentScores
        },
        {
          name: 'Meilleur Score',
          data: bestScores
        }
      ],
      chart: {
        type: 'line',
        height: 250,
        toolbar: { show: false },
        zoom: { enabled: true }
      },
      colors: ['#ff9800', '#4caf50'],
      xaxis: {
        categories: iterations,
        title: {
          text: 'Itération'
        },
        tickAmount: 8, /* Limite l'affichage à 8 étiquettes maximum sur l'axe */
        labels: { 
          style: { fontSize: '11px' },
          rotate: -45, /* Incline le texte pour qu'il ne se chevauche pas */
          hideOverlappingLabels: true /* Sécurité supplémentaire d'ApexCharts */
        }
      },
      yaxis: {
        title: {
          text: 'Score (fonction objectif)'
        },
        labels: { style: { fontSize: '11px' } }
      },
      grid: {
        show: true,
        borderColor: '#f1f1f1'
      },
      legend: {
        position: 'top'
      },
      stroke: {
        curve: 'smooth',
        width: 2
      },
      markers: {
        size: 4
      },
      tooltip: {
        shared: true,
        intersect: false
      }
    };
  }
}
