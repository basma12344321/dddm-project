import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

@Component({
  selector: 'app-analyze-result',
  templateUrl: './analyze-result.component.html',
  styleUrls: ['./analyze-result.component.css']
})
export class AnalyzeResultComponent implements OnInit {
  plugin = '';
  interpretation = '';
  rawResult: any = null;
  radarTitle = '';
  barChartTitle = '';

  // Données graphiques (finance)
  barLabels: string[] = [];
  barValues: number[] = [];
  radarLabels: string[] = [];
  entrepriseRadarData: number[] = [];
  secteurRadarData: number[] = [];
  secteurNom = '';
  roicClass = '';

  // Données Gantt (logistique)
  ganttSeries: any[] = [];
  ganttChartOptions: any = {
  chart: { type: 'rangeBar', height: 350 },
  plotOptions: {
    bar: {
      horizontal: true,
      rangeBarGroupRows: true
    }
  },
  xaxis: {
    type: 'numeric',
    title: { text: 'Temps' }
  },
  yaxis: {
    title: { text: 'Machines' }
  },
  dataLabels: {
    enabled: true,
    formatter: function(val: any, opts: any) {
      return opts.w.globals.initialSeries[opts.seriesIndex].data[opts.dataPointIndex].task;
    }
  }
};

  constructor(private route: ActivatedRoute, private http: HttpClient, private router: Router) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      this.plugin = params['plugin'];
      this.interpretation = params['interpretation'];
      this.rawResult = history.state.result || {};
      console.log("✅ Résultat brut reçu (via state) :", this.rawResult);
      if (this.plugin === 'logistic') {
  setTimeout(() => {
    this.buildGanttChart(this.rawResult.assignments || []);
  }, 0);
}

      this.roicClass = this.getRoicColorClass(this.rawResult.roic || 0);

      if (this.plugin === 'finance') {
        this.loadDashboardData();
      } 
    });
  }

  loadDashboardData(): void {
    this.http.get<any>('http://127.0.0.1:5000/dashboard-data').subscribe(data => {
      this.barLabels = data.classement.labels;
      this.barValues = data.classement.values.map((v: number) => Number(v.toFixed(1)));
      this.radarLabels = data.radar.labels;
      this.entrepriseRadarData = data.radar.entreprise;
      this.secteurRadarData = data.radar.secteur;
      this.secteurNom = data.classement.secteur;
      this.radarTitle = data.radar?.titre || '';
      this.barChartTitle = data.classement?.titre || '';
    });
  }

  getLevelColorClass(niveau: string): string {
    const map: any = {
      'élevé': 'roic-good',
      'moyenne': 'roic-average',
      
      'faible': 'roic-bad'
    };
    return map[niveau?.toLowerCase()] || '';
  }

  getRoicColorClass(roicValue: number): string {
    if (roicValue >= 0.15) return 'roic-good';
    if (roicValue >= 0.05) return 'roic-average';
    return 'roic-bad';
  }

  goToSimulation(): void {
    this.router.navigate(['/simulation'], {
      queryParams: { plugin: this.plugin },
      state: { inputData: this.rawResult.input_data }
    });
  }
  
  buildGanttChart(assignments: any[]) {
    const grouped = new Map<string, any[]>();

    for (const a of assignments) {
      if (a.start_time !== undefined && a.end_time !== undefined) {
        if (!grouped.has(a.machine)) grouped.set(a.machine, []);
        grouped.get(a.machine).push({
          x: a.machine,
          y: [a.start_time, a.end_time],
          task: a.task
        });
      }
    }

    this.ganttSeries = Array.from(grouped.entries()).map(([machine, data]) => ({
      name: machine,
      data
    }));
    console.log("📊 Gantt Series généré :", this.ganttSeries);
    console.log("📊 GanttSeries généré :", JSON.stringify(this.ganttSeries, null, 2));

  }
}
