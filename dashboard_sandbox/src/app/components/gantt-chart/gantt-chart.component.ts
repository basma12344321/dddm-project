import { Component, Input, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgApexchartsModule, ChartComponent } from 'ng-apexcharts';
import {
  ApexAxisChartSeries,
  ApexChart,
  ApexXAxis,
  ApexYAxis,
  ApexTooltip,
  ApexDataLabels,
  ApexPlotOptions,
  ApexLegend,
  ApexMarkers,
  ApexGrid,
  ApexStates
} from 'ng-apexcharts';

export interface GanttChartOptions {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  yaxis: ApexYAxis;
  tooltip: ApexTooltip;
  plotOptions: ApexPlotOptions;
  dataLabels: ApexDataLabels;
  legend: ApexLegend;
  colors: string[];
  grid: ApexGrid;
  states: ApexStates;
  markers: ApexMarkers;
}

export interface GanttTask {
  task: string;
  machine: string;
  start: number;
  end: number;
  duration: number;
  deadline: number;
  priority: number;
  dependencies: string[];
  setup_time: number;
  is_late: boolean;
  tardiness: number;
  status: string;
}

@Component({
  selector: 'app-gantt-chart',
  standalone: true,
  imports: [CommonModule, NgApexchartsModule],
  template: `
    <div class="gantt-container">
      <div class="gantt-header">
        <h4>Diagramme de Gantt - Ordonnancement</h4>
        <div class="gantt-filters">
          <button class="filter-btn" [class.active]="showOnTime" (click)="showOnTime = !showOnTime">
            ✓ On Time
          </button>
          <button class="filter-btn warning" [class.active]="showLate" (click)="showLate = !showLate">
            ⚠ Late
          </button>
          <button class="filter-btn info" (click)="sortByLoad()">
            ↕ Tri charge
          </button>
        </div>
      </div>

      <div id="gantt-chart" *ngIf="chartOptions">
        <apx-chart
          [series]="chartOptions.series"
          [chart]="chartOptions.chart"
          [xaxis]="chartOptions.xaxis"
          [yaxis]="chartOptions.yaxis"
          [tooltip]="chartOptions.tooltip"
          [plotOptions]="chartOptions.plotOptions"
          [dataLabels]="chartOptions.dataLabels"
          [legend]="chartOptions.legend"
          [colors]="chartOptions.colors"
          [grid]="chartOptions.grid"
          [states]="chartOptions.states"
          [markers]="chartOptions.markers"
        ></apx-chart>
      </div>

      <div class="gantt-legend">
        <div class="legend-item">
          <span class="legend-color on-time"></span>
          <span>On Time (dans les temps)</span>
        </div>
        <div class="legend-item">
          <span class="legend-color late"></span>
          <span>En retard</span>
        </div>
        <div class="legend-item">
          <span class="legend-color warning"></span>
          <span>Proche deadline</span>
        </div>
      </div>

      <!-- Task Details Panel -->
      <div class="task-details-panel" *ngIf="selectedTask">
        <div class="panel-header">
          <h5>Tâche: {{selectedTask.task}}</h5>
          <button class="close-btn" (click)="selectedTask = null">×</button>
        </div>
        <div class="panel-content">
          <div class="detail-row">
            <span class="label">Machine:</span>
            <span class="value">{{selectedTask.machine}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Début:</span>
            <span class="value">{{selectedTask.start}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Fin:</span>
            <span class="value">{{selectedTask.end}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Durée:</span>
            <span class="value">{{selectedTask.duration}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Deadline:</span>
            <span class="value">{{selectedTask.deadline}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Priorité:</span>
            <span class="value priority-{{selectedTask.priority}}">{{selectedTask.priority}}</span>
          </div>
          <div class="detail-row">
            <span class="label">Statut:</span>
            <span class="value status-{{selectedTask.status}}">{{selectedTask.status}}</span>
          </div>
          <div class="detail-row" *ngIf="selectedTask.tardiness > 0">
            <span class="label">Retard:</span>
            <span class="value late">+{{selectedTask.tardiness}}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .gantt-container {
      position: relative;
      background: #fff;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    .gantt-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .gantt-header h4 {
      margin: 0;
      color: #333;
      font-weight: 600;
    }

    .gantt-filters {
      display: flex;
      gap: 10px;
    }

    .filter-btn {
      padding: 6px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.2s;
    }

    .filter-btn.active {
      background: #4caf50;
      color: white;
      border-color: #4caf50;
    }

    .filter-btn.warning.active {
      background: #ff9800;
      border-color: #ff9800;
    }

    .filter-btn.info {
      background: #2196f3;
      color: white;
      border-color: #2196f3;
    }

    #gantt-chart {
      min-height: 300px;
    }

    .gantt-legend {
      display: flex;
      gap: 20px;
      margin-top: 15px;
      padding-top: 15px;
      border-top: 1px solid #eee;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    .legend-color {
      width: 16px;
      height: 16px;
      border-radius: 3px;
    }

    .legend-color.on-time { background: #4caf50; }
    .legend-color.late { background: #f44336; }
    .legend-color.warning { background: #ff9800; }

    .task-details-panel {
      position: fixed;
      right: 20px;
      top: 100px;
      width: 300px;
      background: white;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      z-index: 1000;
      animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px;
      border-bottom: 1px solid #eee;
      background: #f8f9fa;
      border-radius: 8px 8px 0 0;
    }

    .panel-header h5 {
      margin: 0;
      color: #333;
    }

    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #666;
      line-height: 1;
    }

    .panel-content {
      padding: 15px;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid #f0f0f0;
    }

    .detail-row:last-child {
      border-bottom: none;
    }

    .detail-row .label {
      color: #666;
      font-size: 13px;
    }

    .detail-row .value {
      font-weight: 500;
      color: #333;
    }

    .priority-1 { color: #4caf50; }
    .priority-2 { color: #ff9800; }
    .priority-3 { color: #f44336; font-weight: 700; }

    .status-on_time { color: #4caf50; }
    .status-late { color: #f44336; }
    .status-warning { color: #ff9800; }

    .value.late {
      color: #f44336;
      font-weight: 700;
    }
  `]
})
export class GanttChartComponent implements OnChanges, AfterViewInit {
  @Input() tasks: GanttTask[] = [];
  @Input() makespan: number = 0;

  chartOptions: GanttChartOptions | null = null;
  selectedTask: GanttTask | null = null;
  showOnTime: boolean = true;
  showLate: boolean = true;
  sortedByLoad: boolean = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tasks'] && this.tasks.length > 0) {
      this.updateChart();
    }
  }

  ngAfterViewInit(): void {
    if (this.tasks.length > 0) {
      this.updateChart();
    }
  }

  updateChart(): void {
    // Grouper par machine
    const machines = [...new Set(this.tasks.map(t => t.machine))].sort();

    // Préparer les données pour le Gantt
    const series: ApexAxisChartSeries = machines.map(machine => {
      const machineTasks = this.tasks
        .filter(t => t.machine === machine)
        .map(t => ({
          x: t.task,
          y: [t.start, t.end],
          fillColor: this.getTaskColor(t),
          taskData: t
        }));

      return {
        name: machine,
        data: machineTasks
      };
    });

    this.chartOptions = {
      series,
      chart: {
        type: 'rangeBar',
        height: 350,
        toolbar: {
          show: true,
          tools: {
            download: true,
            selection: true,
            zoom: true,
            zoomin: true,
            zoomout: true,
            pan: true,
            reset: true
          }
        }
      },
      plotOptions: {
        bar: {
          horizontal: true,
          distributed: false,
          dataLabels: {
            hideOverflowingLabels: false
          }
        }
      },
      dataLabels: {
        enabled: true,
        formatter: function(val, opts) {
          const task = opts.w.config.series[opts.seriesIndex].data[opts.dataPointIndex].taskData;
          return `${task.task} (${task.duration})`;
        },
        style: {
          colors: ['#fff'],
          fontSize: '11px',
          fontWeight: 500
        }
      },
      xaxis: {
        type: 'numeric',
        min: 0,
        max: this.makespan + 2,
        title: {
          text: 'Temps (unités)'
        },
        labels: {
          style: {
            fontSize: '11px'
          }
        }
      },
      yaxis: {
        show: true,
        labels: {
          style: {
            fontSize: '12px',
            fontWeight: 600
          }
        }
      },
      tooltip: {
        custom: ({ seriesIndex, dataPointIndex, w }) => {
          const task = w.config.series[seriesIndex].data[dataPointIndex].taskData;
          return `
            <div class="apex-tooltip">
              <strong>${task.task}</strong><br/>
              Machine: ${task.machine}<br/>
              Début: ${task.start} | Fin: ${task.end}<br/>
              Durée: ${task.duration} | Deadline: ${task.deadline}<br/>
              Statut: ${task.status} ${task.tardiness > 0 ? '(+' + task.tardiness + ')' : ''}
            </div>
          `;
        }
      },
      legend: {
        show: true,
        position: 'top'
      },
      colors: ['#4caf50', '#2196f3', '#ff9800', '#9c27b0', '#f44336', '#00bcd4'],
      grid: {
        show: true,
        borderColor: '#f1f1f1',
        strokeDashArray: 4
      },
      states: {
        active: {
          filter: {
            type: ' lighten',
            value: 0.35
          }
        }
      },
      markers: {
        size: 4,
        colors: ['#fff'],
        strokeColors: '#f44336',
        strokeWidth: 2
      }
    };
  }

  getTaskColor(task: GanttTask): string {
    if (task.is_late) {
      return '#f44336'; // Rouge - en retard
    }
    if (task.deadline - task.end <= 1) {
      return '#ff9800'; // Orange - proche deadline
    }
    return '#4caf50'; // Vert - dans les temps
  }

  sortByLoad(): void {
    this.sortedByLoad = !this.sortedByLoad;
    // Le tri sera géré dans le parent
    this.updateChart();
  }

  onTaskClick(event: any, chart: ChartComponent): void {
    if (event?.dataPointIndex >= 0) {
      const seriesIndex = event.seriesIndex;
      const dataPointIndex = event.dataPointIndex;
      const point = (this.chartOptions?.series[seriesIndex]?.data as any[])?.[dataPointIndex];
      const task = this.tasks.find(t => t.task === point?.x);
      if (task) {
        this.selectedTask = task;
      }
    }
  }
}
