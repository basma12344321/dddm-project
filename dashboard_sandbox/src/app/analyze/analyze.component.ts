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
        const payload = {
          filename: this.file!.name,
          tache: 'classification',
          domaine: this.selectedDomain!
        };

        this.apiService.analyzeFile(payload).subscribe({
          next: (response: any) => {
            this.isLoading = false;
            this.snackBar.open('Analyse terminée avec succès !', 'Fermer', { duration: 3000 });
            this.router.navigate(['/analyze-result'], {
              queryParams: {
                plugin: this.selectedDomain,
                interpretation: response.interpretation_ia || ''
              },
              state: { result: response }
            });
          },
          error: (err) => {
            this.isLoading = false;
            this.error = 'Erreur pendant l\'analyse.';
            console.error('Erreur analyzeFile :', err);
          }
        });
      },
      error: (err) => {
        this.isLoading = false;
        this.error = 'Erreur pendant l\'upload du fichier.';
        console.error('Erreur uploadFile :', err);
      }
    });
  }
}