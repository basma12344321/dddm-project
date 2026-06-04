import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../services/api.service';
import { GanttTask } from '../components/gantt-chart/gantt-chart.component';
import { LogisticsMetrics, ConvergencePoint, OptimizationGain, InterpretationData } from '../components/logistics-dashboard/logistics-dashboard.component';

interface TaskInput {
  Task: string;
  Duration: number;
  Deadline: number;
  Priority?: number;
  Dependencies?: string;
  SetupTime?: number;
  MachineConstraint?: string;
}

@Component({
  selector: 'app-simulation',
  templateUrl: './simulation.component.html',
  styleUrls: ['./simulation.component.css']
})
export class SimulationComponent implements OnInit {
  plugin: string = 'finance';
  result: any = null;
  isLoading = false;
  error: string = '';

  // Données d'entrée
  inputData: any = null;
  tasks: TaskInput[] = [];

  // Paramètres du scheduling
  numMachines: number = 3;
  selectedRule: string = 'EDD';
  rules: { name: string; description: string }[] = [
    { name: 'SPT', description: 'Shortest Processing Time - tâche la plus courte' },
    { name: 'EDD', description: 'Earliest Due Date - deadline la plus proche' },
    { name: 'LPT', description: 'Longest Processing Time - tâche la plus longue' },
    { name: 'WSPT', description: 'Weighted SPT - durée pondérée par priorité' }
  ];

  // Configuration Recuit Simulé
  saConfig = {
    initial_temp: 1000,
    cooling_rate: 0.995,
    min_temp: 0.1,
    max_iterations: 2000
  };

  enableSA: boolean = true;

  // Données pour les graphiques
  ganttTasks: GanttTask[] = [];
  metrics: LogisticsMetrics | null = null;
  convergenceData: ConvergencePoint[] = [];
  optimizationGain: OptimizationGain | null = null;
  interpretation: InterpretationData | null = null;
  executionTimeMs: number = 0;

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.inputData = history.state.inputData || null;
    console.log('📥 Données reçues dans Simulation :', this.inputData);

    this.route.queryParams.subscribe(params => {
      this.plugin = params['plugin'] || 'finance';

      if (this.plugin === 'logistic') {
        this.initLogisticData();
      }
    });
  }

  initLogisticData(): void {
    // Charger les tâches depuis les données d'entrée ou utiliser des exemples
    if (Array.isArray(this.inputData) && this.inputData.length > 0) {
      this.tasks = this.inputData.map((t: any) => ({
        Task: t.Task || t.task || t.task_id || '',
        Duration: parseInt(t.Duration || t.duration || t.Duration || 0),
        Deadline: parseInt(t.Deadline || t.deadline || t.Deadline || 0),
        Priority: t.Priority || t.priority || 1,
        Dependencies: t.Dependencies || t.dependencies || '',
        SetupTime: t.SetupTime || t.setup_time || 0,
        MachineConstraint: t.MachineConstraint || t.machine_constraint || ''
      }));
    } else {
      // Données par défaut
      this.tasks = [
        { Task: 'T0', Duration: 3, Deadline: 6, Priority: 1 },
        { Task: 'T1', Duration: 2, Deadline: 5, Priority: 2 },
        { Task: 'T2', Duration: 4, Deadline: 8, Priority: 1 },
        { Task: 'T3', Duration: 1, Deadline: 4, Priority: 3 },
        { Task: 'T4', Duration: 2, Deadline: 7, Priority: 1 }
      ];
    }
  }

  addTask(): void {
    const newTaskNum = this.tasks.length;
    this.tasks.push({
      Task: `T${newTaskNum}`,
      Duration: 2,
      Deadline: 5,
      Priority: 1
    });
  }

  removeTask(index: number): void {
    this.tasks.splice(index, 1);
  }

  onSubmit(): void {
    this.isLoading = true;
    this.error = '';

    if (this.plugin === 'logistic') {
      this.runScheduling();
    } else {
      this.runFinanceSimulation();
    }
  }

  runScheduling(): void {
    console.log('📤 Envoi des tâches au scheduling:', this.tasks);

    this.apiService.schedule(
      this.tasks,
      this.numMachines,
      this.selectedRule,
      this.enableSA ? this.saConfig : null,
      this.enableSA
    ).subscribe({
      next: (res) => {
        console.log('✅ Résultat scheduling:', res);
        this.result = res;
        this.isLoading = false;

        // Extraire les données pour les graphiques
        if (res.gantt_data) {
          this.ganttTasks = res.gantt_data.map((t: any) => ({
            task: t.task,
            machine: t.machine,
            start: t.start,
            end: t.end,
            duration: t.duration,
            deadline: t.deadline,
            priority: t.priority || 1,
            dependencies: t.dependencies || [],
            setup_time: t.setup_time || 0,
            is_late: t.is_late || false,
            tardiness: t.tardiness || 0,
            status: t.status || 'unknown'
          }));
        }

        if (res.metrics) {
          this.metrics = res.metrics;
        }

        if (res.convergence_data) {
          this.convergenceData = res.convergence_data;
        }

        if (res.optimization_gain) {
          this.optimizationGain = res.optimization_gain;
        }

        if (res.interpretation) {
          this.interpretation = res.interpretation;
        }

        this.executionTimeMs = res.execution_time_ms || 0;
      },
      error: (err) => {
        console.error('❌ Erreur de scheduling', err);
        this.error = err.error?.error || 'Erreur lors du scheduling';
        this.isLoading = false;
      }
    });
  }

  runFinanceSimulation(): void {
    // Simulation finance (inchangée)
    const scenario = this.inputData || {};
    const payload = {
      params: scenario,
      plugin: this.plugin
    };

    this.http.post('http://localhost:5000/simulate', payload).subscribe({
      next: (res) => {
        this.result = res;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('❌ Erreur de simulation', err);
        this.error = err.error?.error || 'Erreur lors de la simulation';
        this.isLoading = false;
      }
    });
  }

  // Changer le nombre de machines
  onMachinesChange(event: any): void {
    this.numMachines = parseInt(event.target.value);
  }

  // Changer la règle heuristique
  onRuleChange(event: any): void {
    this.selectedRule = event.target.value;
  }

  // Activer/désactiver le recuit simulé
  toggleSA(): void {
    this.enableSA = !this.enableSA;
  }
}
