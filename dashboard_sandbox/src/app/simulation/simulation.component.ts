import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

@Component({
  selector: 'app-simulation',
  templateUrl: './simulation.component.html',
  styleUrls: ['./simulation.component.css']
})
export class SimulationComponent implements OnInit {

  simulationForm!: FormGroup;
  plugin: string = 'finance';
  result: any = null;
  isLoading = false;

  inputData: any = null;
  tasks: any[] = []; // utilisé uniquement si plugin = 'logistic'

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private http: HttpClient,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.inputData = history.state.inputData || null;
    console.log("📥 Données reçues dans Simulation :", this.inputData);

    this.route.queryParams.subscribe(params => {
      this.plugin = params['plugin'] || 'finance';

      if (this.plugin === 'finance') {
        this.simulationForm = this.fb.group({
          revenue: ['', Validators.required],
          r_and_d: ['', Validators.required],
          sga: ['', Validators.required]
        });

        if (this.inputData) {
          this.simulationForm.patchValue({
            revenue: this.inputData['Revenue'] || '',
            r_and_d: this.inputData['R&D to Revenue'] || '',
            sga: this.inputData['SG&A to Revenue'] || ''
          });
        }

      } else if (this.plugin === 'logistic') {
        // Cas logistique : on récupère les tâches si dispo, sinon fallback
        if (Array.isArray(this.inputData) && this.inputData.length > 0) {
          this.tasks = [...this.inputData];
        } else {
          this.tasks = [
            { Duration: 3, Deadline: 6 },
            { Duration: 4, Deadline: 10 },
            { Duration: 2, Deadline: 7 },
            { Duration: 5, Deadline: 9 },
            { Duration: 3, Deadline: 8 }
          ];
        }
      }
    });
  }

  onSubmit(): void {
    if (this.plugin === 'finance' && this.simulationForm.invalid) return;

    this.isLoading = true;
    let scenario: any;

    if (this.plugin === 'finance') {
      scenario = {
        Revenue: this.simulationForm.value.revenue,
        'R&D to Revenue': this.simulationForm.value.r_and_d,
        'SG&A to Revenue': this.simulationForm.value.sga,
        EBIT: this.inputData['EBIT'],
        Sector_Grouped: this.inputData['Sector_Grouped']
      };
    } else if (this.plugin === 'logistic') {
      scenario = this.tasks;
    }

    const payload = {
      params: scenario,
      plugin: this.plugin
    };

    const endpoint = this.plugin === 'logistic'
      ? 'http://localhost:5000/schedule'   // ✅ correction ici
      : 'http://localhost:5000/simulate';  // finance reste inchangé

    this.http.post(endpoint, payload).subscribe(
      res => {
        this.result = res;
        this.isLoading = false;
        console.log("✅ Résultat simulation :", res);
      },
      err => {
        console.error('❌ Erreur de simulation', err);
        this.isLoading = false;
      }
    );
  }
}
