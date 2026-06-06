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

interface FinanceParams {
  ebit: number;
  invested_capital: number;
  free_cash_flow: number;
  market_cap: number;
  debt_to_equity: number;
  asset_turnover: number;
  rd_to_revenue: number;
  sga_to_revenue: number;
  sector: string;
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

  // ✅ Paramètres Finance (saisis par l'utilisateur dans le formulaire)
  financeParams: FinanceParams = {
    ebit: 0,
    invested_capital: 0,
    free_cash_flow: 0,
    market_cap: 0,
    debt_to_equity: 0,
    asset_turnover: 0,
    rd_to_revenue: 0,
    sga_to_revenue: 0,
    sector: 'Technology'
  };

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
  interpretationIa: string = '';

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

      // ✅ Pré-remplir financeParams si inputData est disponible (vient de l'analyse)
      if (this.plugin === 'finance' && this.inputData) {
        this.prefillFinanceParams(this.inputData);
      }
    });
  }

  // ✅ Pré-remplir les champs finance depuis les données de l'analyse précédente
  prefillFinanceParams(data: any): void {
    if (!data || typeof data !== 'object') return;
    this.financeParams = {
      ebit:            data.EBIT             || data.ebit             || 0,
      invested_capital: data['Invested Capital'] || data.invested_capital || 0,
      free_cash_flow:  data['Free Cash Flow'] || data.free_cash_flow  || 0,
      market_cap:      data['Market Cap']     || data.market_cap      || 0,
      debt_to_equity:  data['Debt to Equity'] || data.debt_to_equity  || 0,
      asset_turnover:  data['Asset Turnover'] || data.asset_turnover  || 0,
      rd_to_revenue:   data['R&D to Revenue'] || data.rd_to_revenue   || 0,
      sga_to_revenue:  data['SG&A to Revenue']|| data.sga_to_revenue  || 0,
      sector:          data.Sector            || data.sector          || 'Technology'
    };
  }

  initLogisticData(): void {
    if (Array.isArray(this.inputData) && this.inputData.length > 0) {
      this.tasks = this.inputData.map((t: any) => ({
        Task: t.Task || t.task || t.task_id || '',
        Duration: parseInt(t.Duration || t.duration || 0),
        Deadline: parseInt(t.Deadline || t.deadline || 0),
        Priority: t.Priority || t.priority || 1,
        Dependencies: t.Dependencies || t.dependencies || '',
        SetupTime: t.SetupTime || t.setup_time || 0,
        MachineConstraint: t.MachineConstraint || t.machine_constraint || ''
      }));
    } else {
      this.tasks = [
        { Task: 'T0', Duration: 3, Deadline: 6, Priority: 1 },
        { Task: 'T1', Duration: 2, Deadline: 5, Priority: 2 },
        { Task: 'T2', Duration: 4, Deadline: 8, Priority: 1 },
        { Task: 'T3', Duration: 1, Deadline: 4, Priority: 3 },
        { Task: 'T4', Duration: 2, Deadline: 7, Priority: 1 }
      ];
    }
  }

  exportPdfLogistic(): void {
    const payload = {
      metrics:          this.metrics,
      interpretation:   this.interpretation,
      interpretation_ia: this.result?.interpretation_ia || '',
      optimization_gain: this.optimizationGain,
      gantt_data:       this.ganttTasks,
      num_tasks:        this.tasks.length,
      num_machines:     this.numMachines,
      rule:             this.selectedRule
    };

    this.http.post('http://localhost:5000/export-pdf-logistic', payload, {
      responseType: 'blob'
    }).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rapport_logistique_${new Date().toISOString().slice(0,10)}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => console.error('Erreur export PDF logistique:', err)
    });
  }

  addTask(): void {
    const newTaskNum = this.tasks.length;
    this.tasks.push({ Task: `T${newTaskNum}`, Duration: 2, Deadline: 5, Priority: 1 });
  }

  removeTask(index: number): void {
    this.tasks.splice(index, 1);
  }

  onSubmit(): void {
    this.isLoading = true;
    this.error = '';
    this.result = null;

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

        if (res.metrics)           this.metrics = res.metrics;
        if (res.convergence_data)  this.convergenceData = res.convergence_data;
        if (res.optimization_gain) this.optimizationGain = res.optimization_gain;
        if (res.interpretation)    this.interpretation = res.interpretation;
        this.executionTimeMs = res.execution_time_ms || 0;
        if (res.interpretation_ia) this.interpretationIa = res.interpretation_ia;
      },
      error: (err) => {
        console.error('❌ Erreur scheduling', err);
        this.error = err.error?.error || 'Erreur lors du scheduling';
        this.isLoading = false;
      }
    });
  }

  // ✅ CORRIGÉ : envoie financeParams (le formulaire), pas inputData
  runFinanceSimulation(): void {
    // Validation basique
    if (!this.financeParams.ebit && !this.financeParams.invested_capital) {
      this.error = 'Veuillez renseigner au moins EBIT et Capital Investi.';
      this.isLoading = false;
      return;
    }

    const payload = {
      data: {
        'EBIT':              this.financeParams.ebit,
        'Invested Capital':  this.financeParams.invested_capital,
        'Free Cash Flow':    this.financeParams.free_cash_flow,
        'Market Cap':        this.financeParams.market_cap,
        'Debt to Equity':    this.financeParams.debt_to_equity,
        'Asset Turnover':    this.financeParams.asset_turnover,
        'R&D to Revenue':    this.financeParams.rd_to_revenue,
        'SG&A to Revenue':   this.financeParams.sga_to_revenue,
        'Sector':            this.financeParams.sector   // ← clé exacte attendue par preprocess
      },
      plugin: 'finance'
    };
    console.log('📤 Payload simulation finance:', payload);

    this.http.post('http://localhost:5000/simulate', payload).subscribe({
      next: (res: any) => {
        console.log('✅ Résultat simulation finance:', res);
        this.result = res;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('❌ Erreur simulation finance', err);
        // Essayer de lire le message d'erreur du backend
        const backendMsg = err.error?.error || err.error?.message || '';
        this.error = backendMsg || 'Erreur lors de la simulation finance.';
        this.isLoading = false;
      }
    });
  }



  onMachinesChange(event: any): void {
    this.numMachines = parseInt(event.target.value);
  }

  onRuleChange(event: any): void {
    this.selectedRule = event.target.value;
  }

  toggleSA(): void {
    this.enableSA = !this.enableSA;
  }
}