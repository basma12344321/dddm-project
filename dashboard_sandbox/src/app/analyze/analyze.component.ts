import { Component, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';
import { ApiService } from '../services/api.service';

interface Domain {
  name: string;
  value: string;
}

@Component({
  selector: 'app-analyze',
  templateUrl: './analyze.component.html',
  styleUrls: ['./analyze.component.css']
})
export class AnalyzeComponent implements OnInit {
  domains: Domain[] = [
    { name: 'Finance', value: 'finance' },
    { name: 'Logistique', value: 'logistic' }
  ];

  selectedDomain: string | null = null;
  analysisMode: 'file' | 'ticker' = 'file';
  tickerSymbol = '';
  exampleTickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN'];

  file: File | null = null;
  fileName = '';
  isLoading = false;
  error = '';

  analysisResult: any = null;
  logisticsResult: any = null;

  constructor(
    private snackBar: MatSnackBar,
    private http: HttpClient,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {}

  isFormValid(): boolean {
    return !!this.selectedDomain && !!this.file;
  }

  onFileSelected(event: any): void {
    this.handleFile(event.target.files[0]);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  private handleFile(file: File): void {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/csv'
    ];
    if (allowedTypes.includes(file.type) || file.name.endsWith('.csv')) {
      this.file = file;
      this.fileName = file.name;
      this.error = '';
    } else {
      this.error = 'Type de fichier non supporté (CSV ou PDF uniquement)';
    }
  }

  // ✅ Analyse via ticker yfinance
  analyzeTicker(): void {
    if (!this.tickerSymbol) return;

    this.isLoading = true;
    this.error = '';

    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });

    this.http.post(
      'http://127.0.0.1:5000/analyze-ticker',
      { ticker: this.tickerSymbol.toUpperCase() },
      { headers }
    ).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        console.log('Réponse ticker :', response);
        this.snackBar.open(`Analyse de ${this.tickerSymbol} terminée !`, 'Fermer', { duration: 3000 });
        this.router.navigate(['/analyze-result'], {
          queryParams: { plugin: 'finance', interpretation: response.interpretation_ia || '' },
          state: { result: response }
        });
      },
      error: (err) => {
        this.isLoading = false;
        this.error = err.error?.error || `Ticker '${this.tickerSymbol}' introuvable.`;
        console.error('Erreur ticker :', err);
      }
    });
  }

  // ✅ Analyse via fichier CSV
  analyze(): void {
    if (!this.isFormValid()) return;

    this.isLoading = true;
    this.error = '';

    const formData = new FormData();
    formData.append('file', this.file!);

    this.apiService.uploadFile(formData).subscribe({
      next: () => {
        // Pour la logistique, lire le CSV localement et aller vers la simulation.
        if (this.selectedDomain === 'logistic') {
          this.readFileAsText(this.file!)
            .then((csvData: string) => {
              const tasks = this.parseCSVToTasks(csvData);
              this.isLoading = false;
              this.snackBar.open('Fichier uploadé ! Redirection vers la simulation...', 'Fermer', { duration: 3000 });
              this.router.navigate(['/simulation'], {
                queryParams: { plugin: 'logistic' },
                state: { inputData: tasks }
              });
            })
            .catch(() => {
              this.callAnalyzeAPI();
            });
        } else {
          // Finance - appeler l'API d'analyse
          this.callAnalyzeAPI();
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.error = 'Erreur pendant l\'upload du fichier.';
        console.error('Erreur uploadFile :', err);
      }
    });
  }

  private readFileAsText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(file);
    });
  }

  private callAnalyzeAPI(): void {
    const payload = {
      filename: this.file!.name,
      tache: 'classification',
      domaine: this.selectedDomain!
    };

    this.apiService.analyzeFile(payload).subscribe({
      next: (response: any) => {
        this.isLoading = false;
        this.snackBar.open('Analyse terminée avec succès !', 'Fermer', { duration: 3000 });

        // Pour logistic, aller vers simulation
        if (this.selectedDomain === 'logistic') {
          this.router.navigate(['/simulation'], {
            queryParams: { plugin: 'logistic' },
            state: { inputData: response.assignments || [] }
          });
        } else {
          this.router.navigate(['/analyze-result'], {
            queryParams: {
              plugin: this.selectedDomain,
              interpretation: response.interpretation_ia || ''
            },
            state: { result: response }
          });
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.error = 'Erreur pendant l\'analyse.';
        console.error('Erreur analyzeFile :', err);
      }
    });
  }

  private parseCSVToTasks(csvData: string): any[] {
    try {
      const lines = csvData.trim().split(/\r?\n/);
      if (lines.length < 2) return [];

      const delimiter = lines[0].includes(';') && !lines[0].includes(',') ? ';' : ',';
      const headers = lines[0].split(delimiter).map((h: string) => h.trim());
      const tasks: any[] = [];

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(delimiter).map((v: string) => v.trim());
        const task: any = {};

        headers.forEach((header, index) => {
          const value = values[index];
          const normalizedHeader = header.toLowerCase().replace(/[\s_-]/g, '');

          if (normalizedHeader.includes('task') || normalizedHeader.includes('tache')) {
            task.Task = value;
          } else if (normalizedHeader.includes('duration') || normalizedHeader.includes('duree')) {
            task.Duration = parseInt(value) || 0;
          } else if (normalizedHeader.includes('deadline') || normalizedHeader.includes('echeance')) {
            task.Deadline = parseInt(value) || 0;
          } else if (normalizedHeader.includes('priority') || normalizedHeader.includes('priorite')) {
            task.Priority = parseInt(value) || 1;
          } else if (normalizedHeader.includes('dependencies') || normalizedHeader.includes('dependances')) {
            task.Dependencies = value || '';
          } else if (normalizedHeader.includes('setuptime')) {
            task.SetupTime = parseInt(value) || 0;
          } else if (normalizedHeader.includes('machineconstraint') || normalizedHeader.includes('machine')) {
            task.MachineConstraint = value || '';
          }
        });

        if (task.Task && task.Duration) {
          tasks.push(task);
        }
      }
      return tasks;
    } catch (e) {
      console.error('Erreur parsing CSV:', e);
      return [];
    }
  }
}
